<p align="center">
  <img src="https://img.shields.io/badge/Gemini-Flash%20%7C%20Flash--Lite-4285F4?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Arize-Phoenix%20Observability-7C3AED?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Tests-32%20passing-22C55E?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge" />
  <img src="https://img.shields.io/badge/MCP-native-0EA5E9?style=for-the-badge" />
</p>

<h1 align="center">SimAB — Synthetic UX Pretest Engine</h1>

<p align="center">
  <strong>20 AI agents simulate your audience. They evaluate your landing page variants like real people do — one cognitive phase at a time — before you buy a single click of traffic.</strong>
</p>

<p align="center">
  Built for the <a href="https://googlecloudagenthackathon.devpost.com/">Google Cloud Rapid Agent Hackathon</a> · Arize Track
</p>

---

> **v0.3 in development on `feat/resonance-redesign`** — the head-to-head simulator is being replaced with single-variant resonance scoring per [`docs/resonance-redesign.md`](docs/resonance-redesign.md). Existing DBs are not migrated and must be wiped before upgrading.

---

## The problem with A/B testing

Most teams spend $5,000–$50,000 in paid traffic to learn that one of their two landing page variants converts better. By the time the test reaches statistical significance:

- The campaign has already burned most of its budget on the losing variant
- You know **what** won — but not **why**, or which audience segment drove the result
- You get a number, not actionable insight

**SimAB flips this.** Run 20 AI agents before you spend a cent. Each agent embodies a specific audience persona and evaluates your variants the way a real human does — not by answering "do you like this design?" but by thinking through four cognitive phases under realistic constraints.

---

## How it works

```
                    ┌─────────────────────────────────────────────────────┐
                    │              SimAB Agent Pipeline                   │
                    │                                                     │
  Upload 2 images   │  ┌──────────────┐    ┌────────────────┐           │
  + goal + audience │  │BriefNormalizer│───▶│ScenarioBuilder │           │
  ─────────────────▶│  │ (Gemini Flash)│    │(Gemini Flash)  │           │
                    │  └──────────────┘    └───────┬────────┘           │
                    │   • Reads both images         │ 20 scenario cards  │
                    │   • Extracts personas          │ with traffic weights│
                    │   • Detects confounded tests   ▼                   │
                    │                    ┌──────────────────────┐        │
                    │                    │  SimAgent × 20       │        │
                    │                    │  (Gemini Flash-Lite) │        │
                    │                    │  each runs in parallel│       │
                    │                    │                      │        │
                    │   6-phase prompt:  │  1. Anti-cooperative │        │
                    │   "React as THIS   │  2. Logic of Approp. │        │
                    │    person, not as  │  3. System 1 Visual  │        │
                    │    a UX expert"    │  4. System 1 Scanning│        │
                    │                    │  ── SLOW DOWN ──      │        │
                    │                    │  5. System 2 Messaging│       │
                    │                    │  6. System 2 Fogg     │       │
                    │                    └──────────┬───────────┘        │
                    │                               │ 20 SimResults      │
                    │                    ┌──────────▼───────────┐        │
                    │                    │    BiasAuditor        │        │
                    │                    │  (Gemini Flash)       │        │
                    │                    │  Checks position bias │        │
                    │                    │  + confidence collapse │       │
                    │                    └──────────┬───────────┘        │
                    │                               ▼                    │
                    │                    ┌─────────────────────┐         │
                    │                    │     Synthesizer      │         │
                    │                    │  Weighted voting     │         │
                    │                    │  Fogg aggregation    │         │
                    │                    │  Trust gap analysis  │         │
                    │                    │  Friction clustering │         │
                    │                    └──────────┬──────────┘         │
                    └───────────────────────────────┼─────────────────── ┘
                                                    │
                    ┌───────────────────────────────▼────────────────────┐
                    │              Arize Phoenix                          │
                    │   Every Gemini call traced as a span               │
                    │   Full prompt + image + response logged            │
                    │   24+ spans per run, visible in real time          │
                    └────────────────────────────────────────────────────┘
```

**Total runtime: ~90 seconds.** You get a full synthesis: winner, weighted vote, Fogg diagnostics, trust signal gaps, friction themes by persona, attention paths, and messaging alignment — all before touching your ad budget.

---

## What makes this different

### 1. Agents that simulate *cognition*, not just preference

Most AI evaluators ask a single question: "which is better?" SimAB's agents run through six structured phases derived from cognitive science research:

| Phase | Model | What the agent does |
|-------|-------|---------------------|
| **Anti-cooperative constraints** | — | Forced to behave like a flawed, impatient human — not a helpful evaluator |
| **Logic of Appropriateness** | — | 3 self-anchoring questions: "What kind of situation is this? What would someone like me do? Which part of my identity is most relevant?" |
| **Visual Strike** (<500ms) | System 1 | Rates visual impact 1–10 per variant; scores spatial hierarchy alignment against Rule of Thirds |
| **Scanning** (0.5–10s) | System 1 | Decision-style-specific eye movement (F-pattern for analytical, Z-pattern for impulse, trust-first for cautious) with spatial position notes |
| **⟵ SLOW DOWN ⟶** | Boundary | Explicit System 1 → System 2 transition marker |
| **Messaging** (10–60s) | System 2 | Gain/loss framing detection · Trust signal checklist (testimonials, authority, security, risk reversal) · Messaging alignment scoring |
| **Fogg Decision** | System 2 | B = Motivation × Ability × Trigger · Hick's Law CTA count · Patience-threshold abandonment check |
| **Metacognitive Audit** | — | Agent asks itself: "Could I be wrong?" and records self-correction |
| **Behavioral Reminder** | — | Forces re-anchoring to persona identity before submitting |

### 2. Counterbalanced to eliminate position bias

Even-indexed agents see Variant A first. Odd-indexed agents see Variant B first. The `BiasAuditor` then checks whether the winning variant's margin holds after controlling for presentation order. If it doesn't, you get a `trust_level: low` warning before seeing the result.

### 3. Confound detection before you waste agents

The `BriefNormalizer` analyzes both images before building scenarios. If it detects different languages, different brand names, or more than 3 simultaneous variables, it surfaces a `confound_warning` and explains exactly why the test is uninterpretable — before you run 20 agents on a meaningless comparison.

### 4. Traffic-weighted synthesis

Not all segments are created equal. The `ScenarioBuilder` allocates agent count proportionally to each segment's `traffic_weight` using the largest-remainder method. A segment representing 40% of your traffic gets 40% of your agents. The final vote is weighted accordingly.

### 5. Arize Phoenix observability — every Gemini call traced

```python
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317
uvicorn simab.main:app --reload --port 8001
```

Every run produces ~24 spans in Phoenix — one per Gemini call. Each span contains the full prompt (including image inputs), the response, and timing. You can see exactly what the BriefNormalizer extracted, what each SimAgent decided and why, what the BiasAuditor flagged, and what the Synthesizer produced. No black box.

---

## What a PM sees in the dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│  Goal: increase trial signups from landing page                     │
│  run_abc123                                              coverage 82 │
│                                                                     │
│  ┌───────────────── Result ──────────────────────────────┐         │
│  │  VARIANT B  ·  71% weighted vote                      │         │
│  │  "B's single-focus CTA eliminates Hick's Law          │         │
│  │   paralysis. A's 4 competing actions cost it          │         │
│  │   cautious and analytical segments entirely."         │         │
│  └───────────────────────────────────────────────────────┘         │
│                                                                     │
│  Visual Impact ──────────────────────────────────────               │
│  A  ████████░░  7.2/10                                              │
│  B  ██████████  8.8/10  ← visually stronger                        │
│                                                                     │
│  How your personas evaluated it                                     │
│  ┌───────────────────┐  ┌───────────────────┐                      │
│  │ B2B Evaluator     │  │ SMB Founder       │                      │
│  │ ⏱ low patience   │  │ ⏱ medium patience │                      │
│  │ 📊 analytical     │  │ ⚡ impulse         │                      │
│  │ A ██ 20%          │  │ A █████ 50%       │                      │
│  │ B ████████ 80%    │  │ B █████ 50%       │                      │
│  │ Fogg ability: 8/10│  │ Fogg ability: 5/10│                      │
│  │ Missing: reviews  │  │ Missing: price    │                      │
│  └───────────────────┘  └───────────────────┘                      │
│                                                                     │
│  Top friction in Variant A ─────────────────────────────────       │
│  ● HIGH · 4 CTAs competing for attention (Hick's Law)              │
│  ● MED  · No visible pricing anchor for price-sensitive segments   │
│  ● LOW  · Hero image doesn't match B2B context                     │
│                                                                     │
│  Trust signal gaps ─────────────────────────────────────────       │
│  [ testimonials ]  [ money-back guarantee ]  [ security badge ]    │
│                                                                     │
│  Fogg B=MAP Diagnostics ───────────────────────────────────        │
│  Variant A — Motivation: 7.2  Ability: 4.1                         │
│  Variant B — Motivation: 7.0  Ability: 8.3  ← ability gap +4.2    │
│  💡 B scores 4.2pts higher on Ability — the path to conversion     │
│     is dramatically clearer. Apply its CTA structure to A.         │
└─────────────────────────────────────────────────────────────────────┘
```

Every run also produces:
- **Share page** — single self-contained HTML, no JS required, works in any email or Slack link
- **Markdown export** — paste directly into PRDs, Notion, Linear tickets
- **PM-friendly JSON** — plain language, no technical jargon
- **MCP tools** — Claude can run pretests and read results without opening a browser

---

## Quick start — 5 minutes

```bash
git clone https://github.com/Fotomarky/VeraTest.git simab && cd simab
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Free Gemini key — no credit card: https://aistudio.google.com/app/apikey
export GEMINI_API_KEY="..."

# Backend (port 8001 — 8000 is often taken by local services)
uvicorn simab.main:app --reload --port 8001

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000. Upload two screenshots, write a goal, click **Run pretest**. Results stream in live as agents complete.

### With Arize Phoenix tracing

```bash
# Start Phoenix
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

# Backend with OTLP export
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317
pip install -e .[phoenix]
uvicorn simab.main:app --reload --port 8001
```

Open http://localhost:6006. Every Gemini call appears as a span in real time — full prompts, image payloads, responses, and latency.

### With Claude / Cursor via MCP

```bash
pip install -e mcp/
```

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "simab": {
      "command": "python",
      "args": ["-m", "simab_mcp"],
      "env": { "SIMAB_API_URL": "http://localhost:8001" }
    }
  }
}
```

Now ask Claude: *"Run a UX pretest comparing these two screenshots for trial signups from startup founders."*

---

## Architecture

```
simab/
├── agents/
│   ├── normalizer.py    BriefNormalizer — image reading, persona extraction, confound detection
│   ├── scenarios.py     ScenarioBuilder — traffic-weighted allocation, behavioral diversity
│   ├── simulator.py     SimAgent — 6-phase cognitive evaluation per persona
│   ├── auditor.py       BiasAuditor — position bias, confidence collapse, coherence
│   └── synthesizer.py   Synthesizer — weighted voting, Fogg aggregation, trust gap analysis
├── models.py            Pydantic schemas (all new fields backward-compatible)
├── pipeline.py          Sequential orchestration with async parallel sim phase
├── state.py             SQLite via aiosqlite — distributed mutex for idempotent writes
├── main.py              FastAPI — REST + SSE + standalone share page + A2A endpoint
└── llm.py               Gemini client — Flash for orchestration, Flash-Lite for sim agents

frontend/
├── app/
│   ├── page.tsx                    Runs list
│   ├── new/page.tsx                New run form (upload, goal, audience)
│   ├── runs/[id]/page.tsx          Results dashboard (SSE live updates)
│   └── components/
│       ├── PersonaCard.tsx         Per-segment: vote bar, Fogg scores, attention path, trust gaps
│       ├── VisualScores.tsx        Weighted visual impact comparison
│       └── FrictionList.tsx        Expandable friction themes with severity borders

mcp/                                MCP server (stdio, JSON-RPC 2.0)
tests/                              32 tests — schema, state mutex, allocator, aggregation, exports
```

**No LangChain. No LangGraph. No framework.** Pure Python async + stigmergy via shared SQLite state. Agents coordinate through data, not function calls.

---

## Tech stack

| Component | Technology | Role |
|-----------|-----------|------|
| Orchestration LLM | Gemini 2.5 Flash | BriefNormalizer, ScenarioBuilder, BiasAuditor, Synthesizer |
| Simulation LLM | Gemini 2.5 Flash-Lite | 20 SimAgents (cost-optimized, parallel) |
| Observability | **Arize Phoenix** | Full trace of every Gemini call — prompts, images, responses |
| Backend | FastAPI + aiosqlite | REST, SSE streaming, standalone share HTML, A2A protocol |
| State | SQLite (WAL mode) | Shared agent state, distributed mutex, persona library |
| Frontend | Next.js 14 App Router | Live dashboard with SSE, Tailwind CSS |
| MCP server | Python stdio | Claude / Cursor integration, 4 tools |
| Tests | pytest + pytest-asyncio | 32 tests, ~1 second |
| Deployment | Docker / Cloud Run / HF Spaces | See deployment options below |

---

## Tests

```bash
pip install -e .[dev]
pytest tests/ -v
```

```
32 passed in 0.84s
```

Covers: state mutex (idempotent writes under concurrent agents), schema backward compatibility (new fields default safely on old run records), weighted allocator (largest-remainder proportionality), visual impact weighted average, Fogg score aggregation, trust gap frequency ranking, PM-summary translation, markdown export, share-page self-containment, Slack message structure, persona library round-trip.

---

## Deployment options

### Option A — Google Cloud Run (recommended)

```bash
gcloud run deploy simab \
  --source . \
  --region europe-west1 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --memory 1Gi \
  --allow-unauthenticated
```

Free tier: 2M requests/month. Scales to zero. Permanent HTTPS URL.

### Option B — Hugging Face Spaces (always free, no card)

Create a Space → Docker template → push this repo → set `GEMINI_API_KEY` in secrets. URL: `https://<username>-simab.hf.space`

### Option C — Render (free tier)

New Web Service → connect repo → use `Dockerfile` → set `GEMINI_API_KEY`. Sleeps after 15 min idle — good for demos.

### Frontend → Vercel

```bash
cd frontend
vercel --prod   # set NEXT_PUBLIC_API_URL to your backend URL when prompted
```

---

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/runs` | Create run (multipart: `variant_a`, `variant_b`, `goal`, `audience`) |
| GET | `/api/runs` | List recent runs |
| GET | `/api/runs/{id}` | Full run state (JSON) |
| GET | `/api/runs/{id}/stream` | SSE live progress |
| GET | `/api/runs/{id}/summary` | PM-friendly summary |
| GET | `/api/runs/{id}/export.md` | Markdown export |
| GET | `/api/runs/{id}/image/{a\|b}` | Variant image |
| GET | `/share/{id}` | Standalone HTML share page |
| GET | `/api/personas` | Persona library |
| POST | `/a2a/v1/tasks` | A2A protocol |
| GET | `/.well-known/agent-card.json` | Agent marketplace discovery |
| GET | `/health` | Liveness check |
| GET | `/docs` | OpenAPI docs |

---

## MCP tools

| Tool | What it does |
|------|-------------|
| `run_pretest` | Upload two images, goal, and audience — returns run ID and stream URL |
| `get_pretest_result` | Poll or block until a run is complete, returns full synthesis |
| `list_runs` | Show recent runs with status and verdict |
| `list_personas` | Browse the saved persona library |

---

## Slack notifications

```bash
export SIMAB_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Every completed run posts verdict, confidence level, top friction points, and a "View full report" button. No one has to remember to check the dashboard.

---

## Roadmap

**v0.2 — in progress**
- Figma plugin — select two frames, pretest inside the design tool
- GA4 connector UI — validate which tested variant actually lifted post-launch conversion
- Linear webhook — auto-pretest attached screenshots when ticket is labeled `simab:pretest`

**v0.3**
- Persona library wizard — no-code persona editor for PMs
- Notion embed — `/share/{id}` already works in Notion; add one-click pretest from a doc
- Cloud Scheduler weekly audits on live URLs

**v1.0**
- GCP Marketplace listing — Agent Card + A2A endpoints already exist; needs Commerce billing handler
- Gemini Enterprise validation pass

---

## Why this matters

A/B testing is fundamentally broken for most teams. It requires:
1. A live product or staging environment
2. Enough existing traffic to reach significance
3. Weeks of wait time
4. A result that tells you *what* but not *why*

SimAB compresses this to 90 seconds and gives you the *why* — which segment preferred which variant, which trust signals were missing, whether the CTA was cognitively overloaded, and whether the visual hierarchy matched how your audience actually reads.

This isn't a chatbot that answers UX questions. It's a pipeline of agents that executes a structured evaluation protocol, coordinates through shared state, audits its own potential bias, and delivers traceable, reproducible findings — with every reasoning step visible in Arize Phoenix.

---

## License

MIT — see [LICENSE](./LICENSE). Free to self-host, fork, and build on.

## Built with

<p>
  <img src="https://img.shields.io/badge/Google%20Gemini-Flash%20%26%20Flash--Lite-4285F4?logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Arize-Phoenix-7C3AED" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi" />
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/MCP-Model%20Context%20Protocol-0EA5E9" />
</p>
