# Agent Builder layer (ADK) — hackathon-compliance front door

> **Status: scaffold.** This wires the three required technologies together but
> has **not been run against a live GCP project / Phoenix Cloud** yet. Treat the
> steps below as the runbook to validate before submission. See
> `docs/HACKATHON_COMPLIANCE.md` for why this exists.

## What it does

`simab/agent.py` defines a single **ADK `LlmAgent`** ("VeraTest Concierge")
that sits *in front of* the existing, untouched 6-phase pipeline:

```
User ──chat──▶ ADK LlmAgent  (Gemini via Vertex AI = Google Cloud Agent Builder)
                 ├─ tool: start_pretest        → existing pipeline.run_pipeline()
                 ├─ tool: get_pretest_result   → existing state.get_run()
                 └─ MCPToolset → @arizeai/phoenix-mcp   (Arize partner MCP server, live)
```

One component, three requirements satisfied **at runtime**:

| Requirement (Rule §7.A) | How |
|---|---|
| Gemini | The agent's reasoning model (`gemini-2.5-flash`). |
| Google Cloud Agent Builder | ADK is Agent Builder's official SDK; `root_agent` runs on it. |
| Arize partner MCP server | `MCPToolset` spawns `@arizeai/phoenix-mcp` over stdio and the agent calls its tools live. |

The 20-walker pipeline and SQLite state are **unchanged** — they're now the
"tool" this agent wields.

## Run locally

```bash
pip install -e ".[agent]"

# Gemini via Vertex AI (Google Cloud) — closes the "Gemini on Agent Platform" gap
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=veratest-497813
export GOOGLE_CLOUD_LOCATION=us-central1
gcloud auth application-default login        # ADC for Vertex

# Arize Phoenix MCP target (Phoenix Cloud free tier, or self-hosted)
export PHOENIX_BASE_URL=https://app.phoenix.arize.com
export PHOENIX_API_KEY=...

adk web simab        # dev chat UI at http://localhost:8000  (this can be the demo surface)
# or: adk run simab            # terminal chat
# or: adk api_server simab     # REST surface for the frontend / Cloud Run
```

Without `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, ADK falls back to the AI Studio API
(`GOOGLE_API_KEY`) — OK for a quick local smoke test, but **use Vertex for the
judged build.**

## Deploy options (leanest first)

1. **Cloud Run (lean floor).** Containerize `adk api_server simab` as a second
   Cloud Run service. Still "built with Agent Builder." Smallest risk.
2. **Vertex AI Agent Engine (strongest signal, stretch goal).** Unambiguously
   "Agent Builder." Use the helper script:
   ```bash
   gcloud auth application-default login
   gsutil mb -l us-central1 gs://veratest-agent-staging   # one-time
   python scripts/deploy_agent_engine.py --dry-run        # build only, no deploy
   python scripts/deploy_agent_engine.py                  # full deploy
   ```
   Costs the most setup time (IAM, staging bucket, quotas) — only if time allows.

## Validation checklist (do before submitting)
- [ ] `pip install -e ".[agent]"` resolves; confirm the installed `google-adk`
      version matches the `MCPToolset` import path in `agent.py` (adjust if not).
- [ ] `adk web simab` loads and the agent responds via **Vertex** (check the
      Vertex AI request in Cloud console / Phoenix spans).
- [ ] Agent calls `start_pretest` → a run appears in SQLite and the dashboard.
- [ ] Agent calls a **Phoenix MCP tool** (e.g. "list recent runs / experiments")
      and returns real data — this is the partner-MCP-at-runtime evidence.
- [ ] Hosted URL works in a fresh incognito browser.
- [ ] Demo video shows all three (Vertex Gemini, ADK agent, Phoenix MCP call).

## Known caveats
- **ADK MCP import paths drift between releases.** `agent.py` tries the current
  path then an older fallback; pin a known-good `google-adk` once validated.
- **Phoenix MCP server maturity.** `@arizeai/phoenix-mcp` is real but evolving;
  budget one debug loop for tool-schema compatibility with ADK.
- **Image input.** `start_pretest` takes filesystem paths for now (good for the
  demo); wiring chat image uploads through to the pipeline is a follow-up.
