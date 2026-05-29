<p align="center">
  <img src="https://img.shields.io/badge/Google%20Cloud-Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white" />
  <img src="https://img.shields.io/badge/Arize-Phoenix%20Observability-7C3AED?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Gemini-Flash%20%7C%20Flash--Lite-4285F4?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-32%20passing-22C55E?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge" />
  <img src="https://img.shields.io/badge/MCP-native-0EA5E9?style=for-the-badge" />
</p>

<h1 align="center">VeraTest — Know Your Design Works Before You Ship It</h1>

<p align="center">
  <strong>20 AI agents simulate your target audience evaluating your landing page — before you spend a cent on traffic.</strong>
</p>

<p align="center">
  Upload one design for friction analysis. Upload two to find the directional winner.
</p>

<p align="center">
  Built for the <a href="https://googlecloudagenthackathon.devpost.com/">Google Cloud Rapid Agent Hackathon</a> · Arize Track
</p>

---

## The problem with guessing about your design

Most teams ship a design and hope for the best — or burn $10,000–$50,000 in paid traffic running an A/B test to find out which variant converts better. By then:

- The losing variant has already been shown to half your audience
- You know *what* won — but not *why*, or which persona drove it
- You have a number, not a fix

**VeraTest flips this.** Run 20 AI agents in 90 seconds. Each embodies a specific audience persona and evaluates your design the way a real user does — scoring six resonance dimensions, flagging friction, surfacing trust gaps, and telling you exactly what to fix.

No traffic. No guessing. No waiting.

---

## Three evaluation modes

| Mode | What you upload | What you get |
|---|---|---|
| **Single design** | One screenshot | Resonance score, friction themes, trust gaps, sprint stories |
| **A/B pretest** | Two variants | All of the above + directional winner with gap significance |
| **N-variant** *(roadmap)* | 3+ variants | Ranked resonance matrix |

Start with a single design analysis — it's the fastest way to understand your audience before you build variant B.

---

## What PMs get out of every run

Every run produces a **PM Command Center** — a single-page report structured around the decisions a PM actually needs to make:

**CommandRail** — top of page, always visible. Validity badge, overall resonance score (or A vs B tug-of-war), coverage %, and a one-click markdown export for Notion or Linear.

**Sprint Priorities** — top 3 friction themes formatted as sprint tickets, ranked by severity and agent count. Copy them straight into your backlog.

**Blockers & Wins table** — every friction point and what-worked theme in one table. Each row tagged with the cognitive dimension it hits (Motivation↑/↓, Ability↑/↓) and a recommended fix pulled from the agents' metacognitive reflections.

**Persona Carousel** — scroll through each audience segment. See their 6-dimension resonance bars, trust signals found vs missing, and (in A/B mode) which variant they preferred.

**User Story Scaffold** — "As a [persona], I need [fix] so that I can [goal]" cards auto-generated from your high and medium friction themes. Copy-to-clipboard.

**Hypothesis Card** — the single highest-leverage thing to test next, with a projected ability score target.

---

## How the agent pipeline works

```
Upload → BriefNormalizer → ScenarioBuilder → 20 × SimAgent → BiasAuditor → Synthesizer → NarrativeAgents (×3)
```

Six phases, all coordinating through a shared SQLite document — no framework, no LangGraph, no magic. Agents leave structured outputs that downstream agents read, like ants following pheromone trails.

| Phase | Model | What it does |
|---|---|---|
| **BriefNormalizer** | Gemini 2.5 Flash | Reads your image(s), extracts personas, detects confounded tests |
| **ScenarioBuilder** | Gemini 2.5 Flash | Builds 20 micro-varied persona cards, allocates agents by traffic weight |
| **20 × SimAgent** | Gemini 2.5 Flash-Lite | Each agent embodies one persona, evaluates one variant, scores 6 resonance dimensions |
| **BiasAuditor** | Gemini 2.5 Flash | Checks cohort balance, score inflation, rationale coherence |
| **Synthesizer** | Gemini 2.5 Flash | Clusters friction themes, computes gap, sets directional verdict |
| **NarrativeAgents** | Gemini 2.5 Flash | 3 parallel sub-agents: structural diff, hypothesis pros/cons, cohort story |

### The six resonance dimensions

Every SimAgent scores each design on six dimensions — replacing the blunt Fogg motivation/ability binary with a richer diagnostic:

| Dimension | What it captures |
|---|---|
| **Motivation** | Does the design activate the right desire for this persona? |
| **Identity** | Does it speak to who they see themselves as? |
| **Situation** | Does it match the context they're arriving from? |
| **Beliefs** | Does it align with what they already think is true? |
| **Ability** | Is the path to action clear enough for their patience level? |
| **Trigger** | Is the call to action well-timed and hard to miss? |

### Position bias is controlled by design

Even-indexed agents see Variant A first. Odd-indexed agents see Variant B first. The BiasAuditor then checks whether the gap holds after controlling for presentation order — if it doesn't, you get a `trust_level: low` warning before seeing the verdict.

### Confound detection before you waste agents

The BriefNormalizer analyses your images before building scenarios. If it detects different brand names, different languages, or more than three simultaneous variables, it surfaces a `confound_warning` explaining exactly why the test is uninterpretable — before running 20 agents on a meaningless comparison.

---

## Every Gemini call traced with Arize Phoenix

```bash
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317
```

Every run produces ~24 spans in Phoenix — one per Gemini call. Full prompts, image payloads, responses, and timing. You can see exactly what the BriefNormalizer extracted, what each SimAgent decided and why, what the BiasAuditor flagged. No black box.

---

## Quick start — 5 minutes

```bash
git clone https://github.com/Fotomarky/VeraTest.git && cd VeraTest

# Backend
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Free Gemini key — no credit card: https://aistudio.google.com/app/apikey
export GEMINI_API_KEY="your-key-here"

# Smoke tests (no API calls needed)
pytest tests/ -v
# Expected: 32 passed

uvicorn simab.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000. Upload one or two screenshots, write your conversion goal, click **Run**. Results stream in live as agents complete.

### Single-screen analysis

```bash
curl -X POST http://localhost:8000/api/runs \
  -F "variant_a=@your-design.png" \
  -F "goal=sign up for free trial" \
  -F "audience=Startup founders evaluating CI tools"
```

### A/B pretest

```bash
curl -X POST http://localhost:8000/api/runs \
  -F "variant_a=@control.png" \
  -F "variant_b=@challenger.png" \
  -F "goal=sign up for free trial" \
  -F "audience=Startup founders evaluating CI tools"
```

---

## Architecture

```
simab/
├── agents/
│   ├── normalizer.py    Phase 1 — image reading, persona extraction, confound detection
│   ├── scenarios.py     Phase 2 — traffic-weighted allocation, 20 micro-varied cards
│   ├── simulator.py     Phase 3 — 6-dimension resonance evaluation per persona
│   ├── auditor.py       Phase 4 — cohort balance, score inflation, coherence checks
│   ├── synthesizer.py   Phase 5 — friction clustering, gap computation, verdict
│   └── narrative.py     Phase 6 — 3 parallel sub-agents: diff, hypothesis, cohort story
├── models.py            Pydantic schemas (single source of truth)
├── pipeline.py          Sequential orchestration with async parallel sim phase
├── state.py             SQLite WAL — distributed mutex for idempotent writes
├── main.py              FastAPI — REST + SSE + share page + A2A endpoint
└── llm.py               Gemini client — rate limiting, retries, JSON self-healing

frontend/
└── app/
    ├── new/page.tsx               Upload form — single or A/B mode
    ├── runs/[id]/page.tsx         PM Command Center (SSE live updates)
    └── components/
        ├── CommandRail.tsx        Sticky verdict / resonance header
        ├── PackmanTheater.tsx     Pixelated agent animation while in-flight
        ├── SprintPriorities.tsx   Top 3 friction as sprint tasks
        ├── BlockersMatrix.tsx     Friction + wins table with cognitive badges
        ├── PersonaCarousel.tsx    Per-segment resonance deep-dive
        ├── UserStoryScaffold.tsx  Auto-generated user stories from friction
        ├── TestNextHypothesis.tsx Next test recommendation card
        └── VisualEvidence.tsx     Collapsible variant image reference
```

**No LangChain. No LangGraph. No framework.** Pure Python async + stigmergy via shared SQLite. Agents coordinate through data, not function calls — making every run fully debuggable.

---

## Tech stack

| Component | Technology |
|---|---|
| Orchestration | Gemini 2.5 Flash (normalizer, scenarios, auditor, synthesizer, narrative) |
| Simulation | Gemini 2.5 Flash-Lite (20 parallel sim agents — free tier: 1,500/day) |
| Observability | Arize Phoenix (OTLP — full prompt + image + response per span) |
| Backend | FastAPI + aiosqlite + SQLite WAL |
| Frontend | Next.js 14 App Router + Tailwind CSS |
| Deployment | Google Cloud Run (backend 2Gi/2CPU, frontend 512Mi) |
| MCP server | Python stdio, 4 tools |
| Tests | pytest + pytest-asyncio, 32 tests, ~1s |

---

## Deployment — Google Cloud Run

```bash
# Backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/veratest-backend:latest
gcloud run deploy veratest-backend \
  --image gcr.io/$PROJECT_ID/veratest-backend:latest \
  --region us-central1 --memory 2Gi --cpu 2 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest

# Frontend
gcloud builds submit frontend --config frontend/cloudbuild.yaml
gcloud run deploy veratest-frontend \
  --image gcr.io/$PROJECT_ID/veratest-frontend:latest \
  --region us-central1

# Or both at once
./gcp/deploy.sh $PROJECT_ID
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/runs` | Create run (`variant_a`, optional `variant_b`, `goal`, `audience`) |
| GET | `/api/runs/{id}/stream` | SSE live progress |
| GET | `/api/runs/{id}` | Full run state |
| GET | `/api/runs/{id}/export.md` | Markdown export for Notion / Linear |
| GET | `/share/{id}` | Standalone HTML share page (no JS required) |
| GET | `/api/runs/{id}/summary` | PM-friendly plain-language summary |
| POST | `/a2a/v1/tasks` | Google A2A protocol |
| GET | `/.well-known/agent-card.json` | Agent marketplace discovery |

---

## MCP tools — use VeraTest from Claude or Cursor

```bash
pip install -e mcp/
```

```json
{
  "mcpServers": {
    "veratest": {
      "command": "python",
      "args": ["-m", "simab_mcp"],
      "env": { "SIMAB_API_URL": "http://localhost:8000" }
    }
  }
}
```

| Tool | What it does |
|---|---|
| `run_pretest` | Submit images + goal + audience, get run ID |
| `get_pretest_result` | Poll or block until complete, returns full synthesis |
| `list_runs` | Recent runs with status and verdict |
| `list_personas` | Browse the persona library |

Ask Claude: *"Run a pretest on these two screenshots for trial signups from startup founders."*

---

## Tests

```bash
pytest tests/ -v
# 32 passed in ~1s
```

Covers: idempotent state writes under concurrent agents, schema compatibility, traffic-weighted allocator, resonance aggregation, trust gap ranking, markdown export, share-page self-containment.

---

## Roadmap

**Next**
- Figma plugin — pretest frames without leaving the design tool
- GA4 connector — validate which tested variant lifted post-launch conversion
- Linear webhook — auto-pretest when a ticket is labeled `veratest:pretest`

**Later**
- Persona library wizard — no-code persona editor for PMs
- N-variant mode — rank 3+ designs in one run
- GCP Marketplace listing (A2A endpoints already exist)

---

## License

MIT — self-host, fork, and build freely. See [LICENSE](./LICENSE).

<p>
  <img src="https://img.shields.io/badge/Google%20Gemini-Flash%20%26%20Flash--Lite-4285F4?logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Arize-Phoenix-7C3AED" />
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/MCP-Model%20Context%20Protocol-0EA5E9" />
</p>
