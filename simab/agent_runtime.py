"""In-process ADK runtime for the "describe it" input mode.

The `/new` page has two ways to start a pretest:
  - manual: the form posts to POST /api/runs (unchanged)
  - describe: a free-text box posts to POST /api/agent/launch, which calls
    launch_from_description() here.

This drives the VeraTest Concierge agent (simab/agent.py) with a SINGLE turn:
parse the user's paragraph into a conversion goal + audience, then call the
agent's start_pretest tool (which fires the existing pipeline). We return the
run_id so the page can redirect to /runs/{id}. If the description is too vague
for the model to identify a goal, it asks one clarifying question instead and
we surface that back to the page.

The Runner is a long-lived singleton so the @arizeai/phoenix-mcp subprocess is
spawned once (not per request) and we never hit the per-turn MCP teardown hang.
All ADK imports are lazy + guarded so importing this module never fails when the
[agent] extra is absent (e.g. in the test suite).
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

log = logging.getLogger(__name__)

_APP = "veratest_concierge"
_USER = "web"

_runner = None
_session_service = None


def _ensure_runner():
    """Build (once) and return the singleton ADK Runner.

    Raises RuntimeError if the agent isn't available (google-adk not installed
    or the agent failed to build) so callers can return a clean 503.
    """
    global _runner, _session_service
    if _runner is not None:
        return _runner

    from .agent import root_agent  # import-guarded: None when adk is absent
    if root_agent is None:
        raise RuntimeError(
            "Describe mode is unavailable: install the agent extra "
            "(pip install -e '.[agent]') and set the Vertex/Phoenix env vars."
        )

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    _session_service = InMemorySessionService()
    _runner = Runner(agent=root_agent, app_name=_APP, session_service=_session_service)
    log.info("Agent runtime ready (Runner built over root_agent).")
    return _runner


def warmup() -> None:
    """Best-effort build of the Runner at app startup. Never raises."""
    try:
        _ensure_runner()
    except Exception as e:  # pragma: no cover - depends on deploy env
        log.info("Agent runtime warmup skipped: %s", e)


async def launch_from_description(
    description: str,
    variant_a_path: str,
    variant_b_path: Optional[str] = None,
) -> dict:
    """Run one agent turn that launches a pretest from a free-text description.

    Returns either:
      {"run_id": "..."}                       — start_pretest fired; redirect.
      {"needs_clarification": True, "question": "..."} — agent asked for more.
    """
    runner = _ensure_runner()
    from google.genai import types

    session_id = uuid.uuid4().hex
    await _session_service.create_session(
        app_name=_APP, user_id=_USER, session_id=session_id
    )

    paths = f"variant_a_path={variant_a_path}"
    if variant_b_path:
        paths += f", variant_b_path={variant_b_path}"

    prompt = (
        "Start a synthetic UX pretest now by calling the start_pretest tool. "
        "Read the user's description below and extract two things:\n"
        "  - goal: the single conversion action a visitor should take "
        "(e.g. 'start a free trial', 'book a demo', 'compare plans and pick "
        "one'). If the description does not state one explicitly, INFER the "
        "most likely conversion goal from the context.\n"
        "  - audience: who the visitors are, summarized from the description.\n"
        "Use these uploaded screenshot paths EXACTLY as given (do not invent "
        f"paths): {paths}. "
        "ALWAYS call start_pretest — never reply with a question. Make your "
        "best reasonable assumption rather than asking the user for more "
        "detail.\n\n"
        f"User description: {description}"
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    run_id: Optional[str] = None
    final_text = ""
    async for ev in runner.run_async(
        user_id=_USER, session_id=session_id, new_message=msg
    ):
        for part in (ev.content.parts if ev.content else []) or []:
            fr = getattr(part, "function_response", None)
            if fr is not None and fr.name == "start_pretest":
                resp = fr.response or {}
                run_id = resp.get("run_id") or run_id
        if run_id:
            # The pipeline is already launched; the rest of the turn is the
            # model narrating a confirmation we never show. Bail out so the
            # browser redirects ~1-3s sooner. The session is per-request and
            # discarded, so abandoning the turn mid-stream is safe.
            break
        if ev.is_final_response() and ev.content:
            final_text = "".join(
                p.text for p in ev.content.parts if getattr(p, "text", None)
            )

    if run_id:
        return {"run_id": run_id}
    return {
        "needs_clarification": True,
        "question": final_text.strip()
        or "Could you describe the conversion goal and audience in a bit more detail?",
    }
