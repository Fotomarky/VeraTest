# CLAUDE.md — SimAB Developer Reference

> **What this file is:** orientation for Claude Code. Read it once per session before touching any code. It covers architecture, conventions, agent contracts, and common tasks.

---

## Project in one sentence

SimAB is a synthetic UX pretest engine: upload two landing-page screenshots + a conversion goal, and 20 AI agents (each embodying a distinct audience persona) simulate how real users would respond — returning a weighted winner, friction themes, trust signals, and a PM-ready report.

Built for the **Google Cloud Rapid Agent Hackathon — Arize Track**.

---

## Directory map

```
simab/                  Backend Python package (FastAPI)
  main.py               API surface (REST + SSE + A2A endpoints)
  pipeline.py           Orchestrator — runs the 5 phases in sequence
  models.py             ALL Pydantic schemas (single source of truth)
  state.py              SQLite persistence layer (async, WAL mode)
  llm.py                Gemini wrapper — rate limiting, retries, JSON parsing
  config.py             Env-var config (frozen dataclass)
  exports.py            Markdown, PM summary, standalone HTML share page
  agents/
    normalizer.py       Phase 1: parse goal + audience + images → Brief
    scenarios.py        Phase 2: Brief → 3-7 ScenarioCards + allocations
    simulator.py        Phase 3: one ScenarioCard → SimResult (runs 20 in parallel)
    auditor.py          Phase 4: all SimResults → AuditReport (bias checks)
    synthesizer.py      Phase 5: SimResults + AuditReport → Synthesis
  integrations/
    slack.py            Optional: post completion to Slack webhook

mcp/                    MCP server (separate installable package)
  simab_mcp/server.py   4 tools: run_pretest, get_pretest_result, list_runs, list_personas

frontend/               Next.js 14 App Router dashboard
  app/
    page.tsx            Runs list (home)
    new/page.tsx        New run form (upload + goal + audience)
    runs/[id]/page.tsx  Live results page (SSE + all charts)
    components/         Shared UI components

tests/
  test_smoke.py         State, allocator, schema, mutex tests (no API calls)
  test_exports.py       Markdown, share page, PM summary, Slack message tests
  test_visual_evaluation.py  Visual scoring, Fogg model, trust signals tests
  fixtures/
    make_samples.py     Generates variant_a.png + variant_b.png for local testing

validation/
  run.py                Accuracy harness vs baselines (random, always-A, one-shot Gemini)
  dataset.example.csv   5 synthetic examples to verify the harness runs

docs/                   Architecture diagrams and extended reference
```

---

## Architecture: stigmergy (pheromone trail) pattern

**The key design invariant.** Every agent reads from and writes to the shared `Run` document in SQLite. No agent receives parameters from another agent directly. Agents coordinate by leaving structured outputs that downstream agents consume — like ant pheromones.

```
Upload → BriefNormalizer → ScenarioBuilder → 20 × Simulator → BiasAuditor → Synthesizer
           writes brief      writes scenarios   writes SimResults  writes audit   writes synthesis
```

Each agent only writes its own slice:

| Agent | Reads | Writes |
|---|---|---|
| `normalizer` | `goal`, `audience_raw`, images | `run.brief`, `run.scenarios` (inferred_personas) |
| `scenarios` | `run.brief` | `run.scenarios` (final), `run.agent_allocations` |
| `simulator` | `run.scenarios[i]`, images | `run.simulation_results[i]` (idempotent upsert) |
| `auditor` | `run.simulation_results` | `run.audit` |
| `synthesizer` | `run.simulation_results`, `run.audit` | `run.synthesis`, sets status=complete |

**The open/closed rule:** each agent is open to extension (new fields, new heuristics) but closed to upstream changes. An agent must never modify another agent's slice of state.

---

## Models (single source of truth)

`simab/models.py` defines everything. The key types:

- `ScenarioCard` — one persona profile (segment, intent, decision_style, device, traffic_weight, etc.)
- `Brief` — normalizer output (variant summaries, key_differences, inferred_personas)
- `SimResult` — one simulator's verdict (includes Fogg model, trust signals, visual impact)
- `AuditReport` — bias checks (order_bias, confidence_collapse, coherence)
- `Synthesis` — final output (winner, weighted_vote, top_friction, fogg_avg, trust_signal_gaps)
- `Run` — the full shared document containing all of the above

**Never add fields to these models without updating the tests.**

---

## LLM usage

`simab/llm.py` wraps all Gemini calls. Three models:

| Model | Used for | Cost tier |
|---|---|---|
| `gemini-2.5-flash-lite` | 20 sim agents | Free tier: 30 RPM, 1500 RPD |
| `gemini-2.5-flash` | normalizer + scenario builder | Free tier: 15 RPM, 500 RPD |
| `gemini-2.5-pro` | auditor + synthesizer | Free tier: 5 RPM, 50 RPD |

Rate limiting is per-model token buckets in `llm.py`. **Never call `llm.generate()` directly from outside the agents** — rate limiting and retries are baked in.

If a run gets stuck in `simulating`, lower `SIMAB_SIM_CONCURRENCY` (default 6).

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Free key at aistudio.google.com |
| `SIMAB_DB_PATH` | `./simab.db` | SQLite DB path |
| `SIMAB_UPLOAD_DIR` | `./uploads` | Where variant images are stored |
| `SIMAB_SIM_CONCURRENCY` | `6` | Max parallel sim agents |
| `SIMAB_NUM_AGENTS` | `20` | Total sim agents per run |
| `FRONTEND_URL` | `http://localhost:3000` | Used in share URLs |
| `PHOENIX_COLLECTOR_ENDPOINT` | — | Optional: Arize Phoenix OTLP gRPC endpoint |
| `SIMAB_SLACK_WEBHOOK_URL` | — | Optional: post completions to Slack |
| `GA4_CLIENT_ID` / `GA4_CLIENT_SECRET` | — | Optional: import audience from GA4 |

---

## Running the project

### Quick setup (first time)

```bash
# Backend
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
export GEMINI_API_KEY="your-key-here"

# Smoke test (no API needed)
pytest tests/ -v
# Expected: 32 passed

# Generate sample fixtures
python tests/fixtures/make_samples.py

# Start backend
uvicorn simab.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
# Open http://localhost:3000
```

### End-to-end test

```bash
# Submit a run
curl -X POST http://localhost:8000/api/runs \
  -F "variant_a=@tests/fixtures/variant_a.png" \
  -F "variant_b=@tests/fixtures/variant_b.png" \
  -F "goal=sign up for free trial" \
  -F "audience=Startup founders evaluating CI tools"

# Watch SSE stream (replace RUN_ID)
curl -N http://localhost:8000/api/runs/$RUN_ID/stream

# Get markdown export when complete
curl -s http://localhost:8000/api/runs/$RUN_ID/export.md
```

### MCP server

```bash
cd mcp && pip install -e .
# Wire into Claude Desktop config (see TESTING.md §4)
```

---

## Adding a new agent

1. Create `simab/agents/your_agent.py` following the pattern in `auditor.py`:
   - `async def run(run_id: str) -> None`
   - Fetch run from `state.get_run(run_id)`
   - Call `llm.generate()` with the appropriate model
   - Write result back via `state.*` functions
   - Never import from a sibling agent
2. Insert the new phase into `pipeline.py` — update `run_pipeline()` and set the status string via `state.set_status()`
3. Add any new output fields to the relevant model in `models.py`
4. Add tests in `tests/`
5. Run `pytest tests/ -v` — all 32 must pass

---

## API surface

```
REST
  POST /api/runs                  Create + start a run
  GET  /api/runs/{id}             Full run state (JSON)
  GET  /api/runs/{id}/stream      SSE progress updates
  GET  /api/runs                  List recent runs
  GET  /api/runs/{id}/summary     PM-friendly plain-language summary
  GET  /api/runs/{id}/export.md   Markdown export (paste into Notion/Linear)
  GET  /api/runs/{id}/image/{a|b} Serve uploaded variant image
  GET  /api/personas              List saved personas
  GET  /share/{id}                Standalone HTML share page (no JS required)

A2A (Google agent-to-agent protocol)
  GET  /.well-known/agent-card.json  Discovery
  POST /a2a/v1/tasks               Create task (base64 images)
  GET  /a2a/v1/tasks/{id}          Get result

Health
  GET  /health                    {"status":"ok","version":"0.1.0"}
```

---

## Key design decisions to preserve

- **No agent frameworks** (no LangGraph, no CrewAI). All coordination is through SQLite state. This is intentional — it makes the system debuggable without framework abstractions.
- **Idempotent writes.** `simulator.py` writes each `SimResult` with a mutex check so duplicate calls are harmless. Critical for retry safety.
- **SQLite WAL mode.** 20 concurrent writers are safe because WAL handles concurrent reads; the mutex in state.py serialises the writes.
- **Multimodal from the start.** Every Gemini call that involves comparing variants passes both images. The `llm.generate()` wrapper accepts `images: list[bytes]`.
- **JSON self-healing.** When Gemini returns malformed JSON, `llm.py` makes one extra Flash-Lite call to fix it rather than crashing.

---

## Hackathon context

Competition: **Google Cloud Rapid Agent Hackathon — Arize Track**

Track requirements:
- Multi-agent system (✅ 5 agents + 20 parallel sims)
- Arize Phoenix observability integration (✅ OTLP via `PHOENIX_COLLECTOR_ENDPOINT`)
- Open source with detectable license (✅ MIT)
- Live demo URL required
- ~3 minute demo video

**For the Arize track specifically:** start Phoenix (`docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest`) before the demo. Run a pretest live. Show the agent spans in Phoenix at http://localhost:6006 — one span per Gemini call, ~24 per run. This is the single highest-impact thing for the demo video.

**Validation stat (if you run it):** on 20–30 curated tests from ablibrary.de, include the accuracy vs one-shot Gemini comparison in the README and video. Even "73% vs 60%" from a small sample is compelling.

---

## Common tasks

**Check all tests pass before any commit:**
```bash
pytest tests/ -v
```

**Reset local state (wipe DB and uploads):**
```bash
rm -f simab.db && rm -rf uploads/
```

**Check no secrets in staged files:**
```bash
git grep -i "AIza\|sk-\|secret_\|password" -- '*.py' '*.ts' '*.json'
```

**Frontend type-check:**
```bash
cd frontend && npx tsc --noEmit
```
