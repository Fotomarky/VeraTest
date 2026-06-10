"""VeraTest Concierge — the Google Cloud Agent Builder front door.

This module is the hackathon-compliance layer (Arize Track). It wraps the
existing 6-phase SimAB pipeline in a single ADK (Agent Development Kit) agent
so the project satisfies all three required technologies *at runtime*:

  1. Gemini            — the agent's reasoning model (via Vertex AI, see below).
  2. Agent Builder     — ADK is the official SDK for Vertex AI Agent Builder.
  3. Arize MCP server  — the agent mounts `@arizeai/phoenix-mcp` as a live
                         MCP toolset, so it queries Phoenix traces/datasets at
                         runtime (not just OTLP tracing).

The existing pipeline (`simab/pipeline.py`, the 20 cognitive walkers, SQLite
stigmergy state) is DELIBERATELY left untouched. This agent sits *in front* of
it: a PM chats with the agent, it launches a pretest as a tool call, and it
pulls observability insight from Arize Phoenix's MCP server to reason about
quality and prior runs.

--- Running locally -------------------------------------------------------
    pip install -e ".[agent]"          # installs google-adk + deps
    export GOOGLE_GENAI_USE_VERTEXAI=TRUE
    export GOOGLE_CLOUD_PROJECT=veratest-497813
    export GOOGLE_CLOUD_LOCATION=us-central1
    export PHOENIX_BASE_URL=https://app.phoenix.arize.com   # or self-hosted
    export PHOENIX_API_KEY=...                              # Phoenix Cloud key
    adk web simab                      # opens the ADK dev chat UI at :8000
  # or: adk run simab        (terminal)   |   adk api_server simab   (REST)

--- Vertex vs. AI Studio --------------------------------------------------
Setting GOOGLE_GENAI_USE_VERTEXAI=TRUE routes Gemini through Vertex AI on
Google Cloud (satisfies "Gemini models on Agent Platform"). If it is unset,
ADK falls back to the AI Studio Developer API via GOOGLE_API_KEY — fine for
quick local dev, but use Vertex for the judged deployment.

NOTE ON VERSIONS: validated against google-adk==1.34.3 / mcp==1.27.2 (pinned in
pyproject [agent] extra). The MCP toolset import path moved between releases, so
the code below tries the current `McpToolset` name first and falls back to the
deprecated `MCPToolset`. This file is import-guarded so it never breaks the main
FastAPI app when google-adk is absent.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from . import state
from .config import CONFIG
from .pipeline import run_pipeline

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tools — thin wrappers over the EXISTING pipeline. No pipeline changes.
# ---------------------------------------------------------------------------

async def start_pretest(
    goal: str,
    audience: str,
    variant_a_path: str,
    variant_b_path: Optional[str] = None,
) -> dict:
    """Launch a synthetic UX pretest: 20 persona agents evaluate the design(s).

    Provide one screenshot path for single-screen friction analysis, or two
    for an A/B directional comparison. Returns the run_id to poll with
    get_pretest_result.

    Args:
        goal: The conversion goal, e.g. "sign up for free trial".
        audience: Free-text audience description, e.g. "startup founders".
        variant_a_path: Local filesystem path to the first screenshot (PNG/JPG).
        variant_b_path: Optional path to a second screenshot for A/B mode.

    Returns:
        dict with run_id, status, and the dashboard URL.
    """
    run_id = await state.create_run(
        goal=goal,
        audience_raw=audience,
        persona_source="paste",
        variant_a_path=variant_a_path,
        variant_b_path=variant_b_path or None,
    )
    # Fire-and-forget — the pipeline runs in the background just like the
    # REST endpoint does. The agent polls via get_pretest_result.
    asyncio.create_task(run_pipeline(run_id))
    return {
        "run_id": run_id,
        "status": "started",
        "mode": "ab" if variant_b_path else "single_screen",
        "dashboard_url": f"{CONFIG.frontend_url}/runs/{run_id}",
    }


async def get_pretest_result(run_id: str) -> dict:
    """Fetch the current state and (when ready) the synthesized findings.

    Args:
        run_id: The id returned by start_pretest.

    Returns:
        A compact summary: status, and when complete, the directional winner,
        recommendation, top friction themes, and per-cohort resonance.
    """
    run = await state.get_run(run_id)
    if run is None:
        return {"error": f"run {run_id} not found"}

    summary: dict = {"run_id": run_id, "status": run.status}
    syn = getattr(run, "synthesis", None)
    if syn is not None:
        summary.update(
            {
                "directional_winner": getattr(syn, "directional_winner", None),
                "recommendation": getattr(syn, "recommendation", None),
                "cohort_resonance_overall": getattr(syn, "cohort_resonance_overall", None),
                "top_friction": getattr(syn, "top_friction", None),
            }
        )
    return summary


# ---------------------------------------------------------------------------
# Arize Phoenix MCP toolset — the partner MCP server, mounted at runtime.
# ---------------------------------------------------------------------------

def _build_phoenix_toolset():
    """Return an ADK MCP toolset that launches @arizeai/phoenix-mcp via stdio.

    Returns None (so the agent still loads) if the ADK MCP classes can't be
    imported. The subprocess approach means we do NOT host the MCP server
    separately — ADK spawns it and speaks MCP over stdio.

    Validated against google-adk 1.34.3 (see pyproject [agent] extra):
      McpToolset(connection_params=StdioConnectionParams(
          server_params=StdioServerParameters(...)))
    `McpToolset` replaced the deprecated `MCPToolset`; we try the new name
    first and fall back for older releases.
    """
    try:
        from google.adk.tools.mcp_tool import StdioConnectionParams
        try:
            from google.adk.tools.mcp_tool import McpToolset as _Toolset  # adk >= ~1.30
        except Exception:
            from google.adk.tools.mcp_tool import MCPToolset as _Toolset  # older
        from mcp import StdioServerParameters
    except Exception as e:  # pragma: no cover
        log.warning("Phoenix MCP toolset unavailable (%s) — agent loads without it", e)
        return None

    phoenix_env = {
        "PHOENIX_BASE_URL": CONFIG.phoenix_base_url or "http://localhost:6006",
    }
    if CONFIG.phoenix_api_key:
        phoenix_env["PHOENIX_API_KEY"] = CONFIG.phoenix_api_key

    return _Toolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@arizeai/phoenix-mcp@latest"],
                env=phoenix_env,
            )
        )
    )


# ---------------------------------------------------------------------------
# The agent — ADK's CLI/Engine looks for a module-level `root_agent`.
# ---------------------------------------------------------------------------

INSTRUCTION = """\
You are the VeraTest Concierge, a product-research assistant for PMs and \
designers. You help users pretest landing-page designs with a panel of 20 \
synthetic persona agents.

Capabilities:
- Use `start_pretest` to launch a pretest. Ask for the conversion goal, the \
target audience, and at least one screenshot path (two for an A/B test).
- Use `get_pretest_result` to check status and report findings: the \
directional winner, the recommendation, and the top friction themes.
- Use the Arize Phoenix tools to inspect observability data — past runs, \
agent traces, evaluation datasets, and experiments — when the user asks how \
the system or prior tests performed, or to ground a quality claim.

Be concise and decision-oriented. When a pretest is still running, say so and \
offer to check again. Never invent scores — read them from the tools.\
"""


def build_root_agent():
    """Construct the ADK LlmAgent. Separated so import never fails hard."""
    from google.adk.agents import LlmAgent

    tools: list = [start_pretest, get_pretest_result]
    phoenix = _build_phoenix_toolset()
    if phoenix is not None:
        tools.append(phoenix)

    return LlmAgent(
        name="veratest_concierge",
        model="gemini-2.5-flash",  # served via Vertex when GOOGLE_GENAI_USE_VERTEXAI=TRUE
        description="Runs synthetic UX pretests and reports Arize Phoenix insights.",
        instruction=INSTRUCTION,
        tools=tools,
    )


# ADK convention: a module-level `root_agent`. Import-guarded so that merely
# importing this module (e.g. in tests, or when google-adk isn't installed)
# does not raise.
try:
    root_agent = build_root_agent()
except Exception as _e:  # pragma: no cover
    logging.getLogger(__name__).warning(
        "google-adk not available or agent build failed (%s). "
        "Install with: pip install -e \".[agent]\"",
        _e,
    )
    root_agent = None
