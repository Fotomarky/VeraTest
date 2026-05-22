"""SimAB MCP server.

Exposes four tools to MCP clients (Claude Desktop, Cursor, Claude Code):
  - run_pretest         start a pretest from local image files
  - get_pretest_result  poll a previously-started run
  - list_runs           recent runs in the workspace
  - list_personas       saved personas in the workspace

Configure in your MCP client (~/.config/Claude/claude_desktop_config.json):

  {
    "mcpServers": {
      "simab": {
        "command": "python",
        "args": ["-m", "simab_mcp"],
        "env": { "SIMAB_API_URL": "http://localhost:8000" }
      }
    }
  }

Then ask Claude: "Run a UX pretest on these two screenshots for trial signups."
"""
from __future__ import annotations
import asyncio
import os
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SIMAB_API = os.environ.get("SIMAB_API_URL", "http://localhost:8000")

server = Server("simab")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="run_pretest",
            description=(
                "Run a UX pretest comparing two landing-page variants. Returns "
                "weighted winner, confidence level, top friction themes, and "
                "a dashboard URL. Polls until complete (up to ~3 minutes). "
                "Use when the user has two design variants and wants to know "
                "which will convert better with their target audience."
            ),
            inputSchema={
                "type": "object",
                "required": ["variant_a_path", "variant_b_path", "goal"],
                "properties": {
                    "variant_a_path": {
                        "type": "string",
                        "description": "Absolute path to variant A screenshot (PNG/JPG)",
                    },
                    "variant_b_path": {
                        "type": "string",
                        "description": "Absolute path to variant B screenshot (PNG/JPG)",
                    },
                    "goal": {
                        "type": "string",
                        "description": "Conversion goal (e.g. 'sign up for free trial')",
                    },
                    "audience": {
                        "type": "string",
                        "description": (
                            "Audience description: free text, JSON personas, CSV, "
                            "or a campaign brief. Leave empty to infer from variants."
                        ),
                        "default": "",
                    },
                },
            },
        ),
        Tool(
            name="get_pretest_result",
            description="Fetch the current state of a pretest run by ID.",
            inputSchema={
                "type": "object",
                "required": ["run_id"],
                "properties": {"run_id": {"type": "string"}},
            },
        ),
        Tool(
            name="list_runs",
            description="List recent SimAB pretest runs in this workspace.",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 10}},
            },
        ),
        Tool(
            name="list_personas",
            description="List saved personas in the workspace library.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Optional tag filter"}
                },
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _wait_for_complete(client: httpx.AsyncClient, run_id: str, timeout_s: int = 240) -> dict:
    """Poll the run endpoint until status is complete or failed."""
    for _ in range(timeout_s):
        resp = await client.get(f"/api/runs/{run_id}")
        if resp.status_code != 200:
            return {"error": f"Could not fetch run: {resp.status_code}"}
        run = resp.json()
        if run["status"] in ("complete", "failed"):
            return run
        await asyncio.sleep(1)
    return {"error": "Timed out waiting for run to complete"}


def _format_result(run: dict) -> str:
    """Pretty-print run result for chat display."""
    if run.get("error"):
        return f"❌ Error: {run['error']}"
    if run["status"] == "failed":
        return f"❌ Run failed: {run.get('error', 'unknown error')}"
    if run["status"] != "complete":
        # In progress — show what we have
        completed = len(run.get("simulation_results", []))
        return (
            f"⏳ Run **{run['run_id']}** still in progress\n"
            f"   Status: {run['status']}\n"
            f"   Simulations completed: {completed}\n"
            f"   Use `get_pretest_result` with this run_id to check again."
        )

    synth = run.get("synthesis") or {}
    audit = run.get("audit") or {}

    lines = ["# UX Pretest Result", ""]

    # Trust banner first (if not high)
    if audit.get("trust_level") != "high":
        lines.append(f"⚠️  **Trust level: {audit.get('trust_level','?').upper()}**")
        for w in audit.get("warnings", [])[:3]:
            lines.append(f"   - {w}")
        lines.append("")

    winner = synth.get("winner", "?")
    weighted = synth.get("weighted_vote", {})
    weighted_pct = (
        f"{weighted.get(winner, 0):.0%}" if winner in weighted else "?"
    )
    lines.extend([
        f"**Winner:** {winner.upper()} ({weighted_pct} weighted vote)",
        f"**Coverage:** {synth.get('coverage_score', 0)}/100",
        "",
        f"_{synth.get('one_line_summary', '')}_",
        "",
    ])

    if synth.get("top_friction"):
        lines.append("## Top friction (in the losing variant)")
        for t in synth["top_friction"][:5]:
            lines.append(f"- **{t['theme']}** ({t['count']} mentions, {t['severity']})")
        lines.append("")

    if synth.get("segment_splits"):
        lines.append("## Segment splits")
        for seg, splits in list(synth["segment_splits"].items())[:5]:
            pct = ", ".join(f"{k}: {v:.0%}" for k, v in splits.items())
            lines.append(f"- {seg} — {pct}")
        lines.append("")

    if synth.get("recommendation"):
        lines.append(f"**Recommendation:** {synth['recommendation']}")
        lines.append("")

    lines.append(f"Run ID: `{run['run_id']}`")
    return "\n".join(lines)


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with httpx.AsyncClient(base_url=SIMAB_API, timeout=httpx.Timeout(300.0)) as client:
        try:
            if name == "run_pretest":
                a_path = Path(arguments["variant_a_path"])
                b_path = Path(arguments["variant_b_path"])
                if not a_path.exists():
                    return [TextContent(type="text", text=f"❌ File not found: {a_path}")]
                if not b_path.exists():
                    return [TextContent(type="text", text=f"❌ File not found: {b_path}")]

                with open(a_path, "rb") as fa, open(b_path, "rb") as fb:
                    resp = await client.post(
                        "/api/runs",
                        files={
                            "variant_a": (a_path.name, fa, "image/png"),
                            "variant_b": (b_path.name, fb, "image/png"),
                        },
                        data={
                            "goal": arguments["goal"],
                            "audience": arguments.get("audience", ""),
                        },
                    )
                if resp.status_code not in (200, 201):
                    return [TextContent(
                        type="text",
                        text=f"❌ Failed to create run: {resp.status_code} {resp.text}",
                    )]
                run_id = resp.json()["run_id"]
                final = await _wait_for_complete(client, run_id)
                return [TextContent(type="text", text=_format_result(final))]

            if name == "get_pretest_result":
                resp = await client.get(f"/api/runs/{arguments['run_id']}")
                if resp.status_code != 200:
                    return [TextContent(
                        type="text", text=f"❌ Not found: {arguments['run_id']}"
                    )]
                return [TextContent(type="text", text=_format_result(resp.json()))]

            if name == "list_runs":
                limit = arguments.get("limit", 10)
                resp = await client.get(f"/api/runs?limit={limit}")
                runs = resp.json()
                if not runs:
                    return [TextContent(type="text", text="No runs yet.")]
                lines = ["# Recent runs", ""]
                for r in runs:
                    winner = (r.get("synthesis") or {}).get("winner", "—")
                    lines.append(
                        f"- `{r['run_id']}` · {r['status']} · "
                        f"goal: \"{r['goal'][:50]}\" · winner: {winner}"
                    )
                return [TextContent(type="text", text="\n".join(lines))]

            if name == "list_personas":
                tag = arguments.get("tag")
                params = {"tag": tag} if tag else {}
                resp = await client.get("/api/personas", params=params)
                personas = resp.json()
                if not personas:
                    return [TextContent(type="text", text="No saved personas.")]
                lines = ["# Saved personas", ""]
                for p in personas:
                    lines.append(
                        f"- **{p['segment']}** ({p['device']}, {p['intent']}) — "
                        f"`{p['id']}`"
                    )
                return [TextContent(type="text", text="\n".join(lines))]

            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

        except httpx.ConnectError:
            return [TextContent(
                type="text",
                text=(
                    f"❌ Could not reach SimAB backend at {SIMAB_API}.\n"
                    "Start it with: `uvicorn simab.main:app --port 8000`"
                ),
            )]


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    asyncio.run(_run())


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    main()
