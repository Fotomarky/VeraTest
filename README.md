<p align="center">
  <img src="https://img.shields.io/badge/Google%20Cloud-Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white" />
  <img src="https://img.shields.io/badge/Arize-Phoenix%20Observability-7C3AED?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Gemini-Flash%20%7C%20Flash--Lite-4285F4?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-79%20passing-22C55E?style=for-the-badge" />
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
| **N-variant** *(roadmap)* | 3+ variants | Ranked resonance matrix | (in pipeline) 

Start with a single design analysis — it's the fastest way to understand your audience before you build variant B.

---

## What PMs get out of every run

Every run produces a **PM Command Center** — a single-page report structured around the decisions a PM actually needs to make:

**CommandRail** — top of page, always visible. Validity badge, persona-fidelity badge ("18/20 in persona"), overall resonance score (or A vs B tug-of-war), coverage %, and a one-click markdown export for Notion or Linear.

**Your Audience Personas** — a PageSpeed-style hero of persona circles, one per audience segment, each ring showing its lean (positive/negative, or A/B). Click any circle to expand its full 6-dimension resonance breakdown, trust signals, and which variant it preferred.

**What to do next** — the single recommendation plus the top high/medium friction items rephrased as positive, shippable actions ("Add concrete use cases"), each tagged with the agent count it affects and a projected ability-score target.

**Conversion Blockers & Wins** — every friction point and what-worked theme in one table. Each row tagged with the cognitive dimension it hits (Motivation↑/↓, Ability↑/↓) and a recommended fix pulled from the agents' metacognitive reflections.

**User Stories to Write** — "As a [persona], I need [fix] so that I can [goal]" cards auto-generated from your high and medium friction themes, phrased as positive needs. Copy-to-clipboard.

**Visual Reference** — collapsible variant image reference (collapsed by default when the test is confounded).

---

## Why this works

VeraTest doesn't invent a methodology. It digitizes one. Every layer in the pipeline maps to an established practice from UX research, cognitive science, or experimental design — fields with decades of evidence behind them. The question isn't whether the methodology is sound. It's whether AI agents can execute it faithfully enough to be useful.

### 1. The methodology is established

**Multiple independent evaluators beat any single expert.** Nielsen (1994) demonstrated that 5 independent evaluators find ~80% of usability issues; 15 find ~90%. Condorcet's jury theorem formalizes why: independent judges with better-than-random individual accuracy converge on the correct answer as panel size grows. VeraTest uses 20 — each constrained to a different persona, eliminating the groupthink that a single LLM call would produce.

**Structured evaluation outperforms open-ended preference.** Decades of industrial/organizational psychology show that structured interviews predict outcomes 2× better than unstructured ones (Schmidt & Hunter, 1998). The same principle applies to design evaluation. Asking "which is better?" produces confident noise. Walking through a defined protocol — visual impact, scanning path, trust signals, cognitive load — produces diagnostics.

**System 1 → System 2 progression mirrors real cognition.** Kahneman's dual-process theory isn't a hypothesis — it's textbook cognitive science. Humans process a landing page in two distinct phases: fast visual/emotional reaction (System 1), then slow deliberate reading and decision-making (System 2). VeraTest's Cognitive Walkers follow this sequence because that's how brains actually process a page, not because it's a convenient architecture choice.

**The Fogg Behavior Model (B = MAP) drives the decision layer.** One of the most cited frameworks in persuasive design: Behavior = Motivation × Ability × Trigger. VeraTest's six resonance dimensions extend Fogg with Identity (Social Identity Theory), Situation (Situated Cognition), and Beliefs (Cognitive Dissonance Theory) — producing a richer diagnostic than any single framework alone.

**Counterbalancing and confound detection are Experimental Design 101.** Showing Variant A first to half the panel and B first to the other half is the minimum methodological standard for any comparison study. Rejecting tests where both variants differ in language, brand, and layout simultaneously is what any research director or IRB would do. Most AI evaluation tools skip both. VeraTest does neither.

### 2. LLM persona simulation is emerging but credible

Can language models actually simulate how different people evaluate a design? The evidence is early but directional:

- **Argyle et al. (2023), "Out of One, Many"** — demonstrated that LLMs can reproduce demographic subgroups' survey responses with surprising accuracy across age, income, and political affiliation. The paper calls this "silicon sampling."
- **Aher et al. (2023), "Using LLMs to Simulate Multiple Humans"** — replicated classic behavioral experiments (ultimatum game, Milgram-style studies) using LLM personas and got results that matched original human data.
- **Park et al. (2023), "Generative Agents"** — 25 LLM agents in a simulated town exhibited emergent social behaviors that human evaluators rated as more human-like than actual human transcripts.

VeraTest adds structural constraints that these papers identify as critical: persona locking (agents can't drift toward "helpful AI evaluator" mode), anti-cooperative prompting (agents are forced to behave like impatient, flawed humans), and metacognitive self-audit (agents check their own reasoning for persona leakage before submitting).

### 3. This replaces guessing, not clinical trials

AI persona simulation is not a replacement for real traffic data. It's a replacement for the alternative — which, for most teams, is a PM's intuition, a Slack poll, or shipping the founder's favorite and hoping for the best.

The question isn't *"is this as reliable as a 50,000-visitor A/B test with 95% statistical significance?"* It's *"is this more reliable than no test at all?"* The methodology says yes. The emerging LLM research says yes. And VeraTest's own validation against known A/B outcomes provides a concrete accuracy number you can evaluate for yourself (see [Validation](#validation)).

A $50,000 A/B test is more rigorous. But you need a live product, real traffic, and 4–6 weeks. VeraTest gives you a directional signal in 90 seconds, before you've written a single line of code for Variant B — so you can build the right variant and save the real test for final confirmation.

---

## How the agent pipeline works

Six agents, six phases. Each one mirrors a role in a professional usability study. Remove any layer and the results break in the same way a sloppy research study produces misleading data.

```
Upload → Study Designer → Panel Recruiter → 20 × Cognitive Walkers → Bias Auditor → Insight Analyst → Report Narrators (×3)
```

| Phase | Agent | Research equivalent | Model | What breaks without it |
|---|---|---|---|---|
| 1 | **Study Designer** | Research director who reads the brief | Gemini Flash | You test noise — confounded comparisons produce uninterpretable data |
| 2 | **Panel Recruiter** | Recruiter assembling a representative panel | Gemini Flash | Niche 5% segments get equal voice to your core 60% audience |
| 3 | **Cognitive Walker** ×20 | Moderated cognitive walkthrough session | Gemini Flash-Lite | You're asking "which do you prefer?" — confident noise, no diagnostics |
| 4 | **Bias Auditor** | Methodologist checking data quality | Gemini Flash | Position effects silently corrupt your results |
| 5 | **Insight Analyst** | Analyst synthesizing session transcripts | Gemini Flash | You have 20 opinions; opinions aren't findings |
| 6 | **Report Narrator** ×3 | Research debrief writer | Gemini Flash | PMs get dashboards of numbers, not decisions for sprint planning |

### Phase 1 · Study Designer

Before a single agent evaluates your design, the Study Designer reads your image(s), extracts who your audience actually is, and checks for confounds. Different languages between variants? Different brand names? More than three simultaneous changes? It flags the test as uninterpretable — before you waste 20 evaluations on a comparison that can't produce a valid result.

### Phase 2 · Panel Recruiter

Builds 20 persona cards — each with a specific segment, intent, decision style, patience threshold, and device. Allocates agents proportionally to each segment's traffic weight using the largest-remainder method. A segment representing 40% of your traffic gets 40% of your evaluators. The synthesis reflects your actual audience, not an equal-weighted fiction.

### Phase 3 · Cognitive Walkers (×20, parallel)

The core of VeraTest. Each Cognitive Walker embodies one persona and evaluates your design through a structured cognitive sequence:

| Step | Cognitive mode | What the agent does |
|---|---|---|
| Identity anchoring | Pre-evaluation | Locks to the persona: "What kind of person am I? What situation am I arriving from?" |
| Gut reaction | System 1 | Rates visual impact, reads spatial hierarchy. First impressions form in <500ms. |
| Scanning | System 1 | Follows the eye path dictated by decision style — F-pattern (analytical), Z-pattern (impulse), trust-first (cautious). |
| Deliberate evaluation | System 2 | Reads messaging, checks trust signals, scores alignment with existing beliefs. |
| Decision | System 2 | Fogg model: B = Motivation × Ability × Trigger. Is the path clear enough for this persona's patience level? |
| Self-audit | Metacognitive | "Could I be wrong? Am I responding as this persona, or as a helpful AI?" |

Every agent scores six resonance dimensions, producing a diagnostic fingerprint rather than a blunt preference:

| Dimension | What it captures | Framework origin |
|---|---|---|
| **Motivation** | Does the design activate the right desire? | Fogg Behavior Model |
| **Identity** | Does it speak to who they see themselves as? | Social Identity Theory |
| **Situation** | Does it match the context they're arriving from? | Situated Cognition |
| **Beliefs** | Does it align with what they already think is true? | Cognitive Dissonance Theory |
| **Ability** | Is the path to action clear enough for their patience? | Fogg Behavior Model |
| **Trigger** | Is the CTA well-timed and unmissable? | Fogg Behavior Model |

### Phase 4 · Bias Auditor

Even-indexed agents see Variant A first; odd-indexed agents see Variant B first. The Bias Auditor checks whether the margin holds after controlling for presentation order. It also flags confidence collapse (suspiciously uniform scores), cohort imbalance, and rationale incoherence. If the result doesn't survive these checks, you see `trust_level: low` before the verdict — not after you've acted on it.

### Phase 5 · Insight Analyst

Takes 20 individual evaluations and produces findings: directional winner, resonance gap with significance assessment, friction themes clustered by severity and agent count, what-worked themes, trust signal gaps, and a single recommendation for what to fix first. Twenty opinions become one synthesis.

### Phase 6 · Report Narrators (×3, parallel)

Three parallel sub-agents each write one section of the PM report:

| Narrator | What it produces |
|---|---|
| **Structural Diff** | What's objectively different between the variants and how it maps to the resonance gap |
| **Hypothesis** | The single highest-leverage thing to test next, with a projected improvement target |
| **Cohort Story** | How each audience segment responded differently — the "why behind the why" |

### Position bias is controlled by design

Even-indexed agents see Variant A first. Odd-indexed agents see Variant B first. The Bias Auditor then checks whether the gap holds after controlling for presentation order — if it doesn't, you get a `trust_level: low` warning before seeing the verdict.

### Confound detection before you waste agents

The Study Designer analyses your images before building scenarios. If it detects different brand names, different languages, or more than three simultaneous variables, it surfaces a `confound_warning` explaining exactly why the test is uninterpretable — before running 20 agents on a meaningless comparison.

---

## Every Gemini call traced with Arize Phoenix

```bash
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317
```

Every run produces ~24 spans in Phoenix — one per Gemini call. Full prompts, image payloads, responses, and timing. You can see exactly what the Study Designer extracted, what each Cognitive Walker decided and why, what the Bias Auditor flagged. No black box.

### Cross-run calibration — agents that improve

A 7th agent — **FidelityAuditor** — runs an LLM-as-a-Judge persona-
consistency eval plus a code-based rationale-coherence check on every run.
Drifted agents are written to a persistent Phoenix Dataset; on the next
run targeting a similar audience, ScenarioBuilder queries that history and
strengthens the prompt of any persona archetype that has drifted >25% of
the time. The Command Center surfaces this as a "95% in character" badge —
the answer to "how do I trust this?"

See [scripts/run_calibration_experiment.py](scripts/run_calibration_experiment.py)
for the baseline-vs-tightened Phoenix Experiment that produces the
visible before/after fidelity delta.

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
# Expected: 79 passed

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
│   ├── normalizer.py    Phase 1 · Study Designer — image reading, persona extraction, confound detection
│   ├── scenarios.py     Phase 2 · Panel Recruiter — traffic-weighted allocation, 20 micro-varied cards
│   ├── simulator.py     Phase 3 · Cognitive Walker (×20) — 6-dimension resonance evaluation per persona
│   ├── auditor.py       Phase 4 · Bias Auditor — cohort balance, score inflation, coherence checks
│   ├── synthesizer.py   Phase 5 · Insight Analyst — friction clustering, gap computation, verdict
│   └── narrative.py     Phase 6 · Report Narrators (×3) — diff, hypothesis, cohort story
├── models.py            Pydantic schemas (single source of truth)
├── pipeline.py          Sequential orchestration with async parallel sim phase
├── state.py             SQLite WAL — distributed mutex for idempotent writes
├── main.py              FastAPI — REST + SSE + share page + A2A endpoint
├── llm.py               Gemini client — rate limiting, retries, JSON self-healing
└── agent.py             Agent Builder (ADK) front door — wraps the pipeline as tools + Arize Phoenix MCP toolset

frontend/
└── app/
    ├── new/page.tsx               Upload form — single or A/B mode
    ├── runs/[id]/page.tsx         PM Command Center (SSE live updates)
    └── components/
        ├── CommandRail.tsx        Sticky verdict / resonance / fidelity header
        ├── ResultsHero.tsx        Persona-circles hero (uses PersonaCard)
        ├── PersonaCard.tsx        Single persona's resonance + trust deep-dive
        ├── PackmanTheater.tsx     Pixelated agent animation while in-flight
        ├── WhatToDoNext.tsx       Recommendation + positive next-step actions
        ├── BlockersMatrix.tsx     Friction + wins table with cognitive badges
        ├── UserStoryScaffold.tsx  Auto-generated user stories from friction
        └── VisualEvidence.tsx     Collapsible variant image reference
```

**A framework-free core behind an Agent Builder front door.** The 6-phase
pipeline coordinates through a single shared SQLite document — every agent
reads from and writes to one structured record (stigmergy) — so each run is
fully inspectable and every Gemini call is a direct OpenInference span, with
no framework intermediation to obscure what the agent saw and decided. That
transparent core is left **untouched**. In front of it sits a thin **Google
Cloud Agent Builder** layer (`simab/agent.py`): a single ADK `LlmAgent`
("VeraTest Concierge") that a PM chats with. It exposes the pipeline as two
tools (`start_pretest`, `get_pretest_result`) and mounts the **Arize Phoenix
MCP server** (`@arizeai/phoenix-mcp`) as a live MCP toolset, so it can query
traces, datasets, and prior runs at runtime. See
[`docs/agent-builder.md`](docs/agent-builder.md).

---

## Google Cloud Agent Builder layer (ADK)

```
User ──chat──▶ ADK LlmAgent  (Gemini via Vertex AI = Google Cloud Agent Builder)
                 ├─ tool: start_pretest        → existing pipeline.run_pipeline()
                 ├─ tool: get_pretest_result   → existing state.get_run()
                 └─ MCPToolset → @arizeai/phoenix-mcp   (Arize partner MCP server, live)
```

One component satisfies all three Arize-track requirements **at runtime**:
Gemini (the agent's reasoning model, served via Vertex AI when
`GOOGLE_GENAI_USE_VERTEXAI=TRUE`), Google Cloud Agent Builder (ADK is its
official SDK), and the Arize partner MCP server (mounted as a live toolset).

```bash
pip install -e ".[agent]"
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=veratest-497813 GOOGLE_CLOUD_LOCATION=us-central1
gcloud auth application-default login
export PHOENIX_BASE_URL=https://app.phoenix.arize.com PHOENIX_API_KEY=...
adk web simab        # dev chat UI at http://localhost:8000
```

Deploy to **Vertex AI Agent Engine** with `python scripts/deploy_agent_engine.py`
(use `--dry-run` to build without deploying), or run `adk api_server simab` as a
second Cloud Run service. The 20-walker pipeline and SQLite state are unchanged.

---

## Tech stack

| Component | Technology |
|---|---|
| Agent Builder | Google ADK `LlmAgent` (`simab/agent.py`) — Vertex AI Agent Engine / Cloud Run |
| Orchestration | Gemini 2.5 Flash (Study Designer, Panel Recruiter, Bias Auditor, Insight Analyst, Report Narrators) |
| Simulation | Gemini 2.5 Flash-Lite (20 parallel Cognitive Walkers — free tier: 1,500/day) |
| Observability | Arize Phoenix (OTLP tracing — full prompt + image + response per span) |
| Partner MCP | `@arizeai/phoenix-mcp` mounted as a live ADK MCP toolset |
| Backend | FastAPI + aiosqlite + SQLite WAL |
| Frontend | Next.js 14 App Router + Tailwind CSS |
| Deployment | Google Cloud Run (backend 2Gi/2CPU, frontend 512Mi) |
| MCP server | Python stdio, 4 tools |
| Tests | pytest + pytest-asyncio, 79 tests, ~2s |

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

### Phoenix MCP — runtime introspection of your own traces

The Arize track requires agents to introspect their operational data at
runtime via the Phoenix MCP server. Drop this into any MCP client config —
Claude Desktop, Gemini CLI, Cursor — alongside the VeraTest MCP server:

```bash
cp mcp/phoenix-mcp.example.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Then ask Claude (or Gemini CLI):

> *"Which personas drifted in the last 5 VeraTest runs, and what was their
> average rationale coherence?"*

The Phoenix MCP server exposes Datasets, Experiments, Prompts, and Spans
as MCP tools — so your assistant can query them directly, no SQL required.

Ask Claude: *"Run a pretest on these two screenshots for trial signups from startup founders."*

---

## Tests

```bash
pytest tests/ -v
# 79 passed in ~2s
```

Covers: idempotent state writes under concurrent agents, schema compatibility, traffic-weighted allocator, resonance aggregation, trust gap ranking, markdown export, share-page self-containment, and the describe-mode HTTP surface (upload sanitization, orphan cleanup, agent-unavailable degradation).

---

## Validation

Most AI evaluation tools ask you to trust them. VeraTest ships a falsifiable benchmark you can re-run yourself.

### The harness

`validation/run.py` scores the full 20-agent pipeline against real A/B tests with publicly documented winners ([abtestcases.com](https://www.abtestcases.com)), alongside four baselines:

| Baseline | What it controls for |
|---|---|
| `random` | Floor — is anything better than a coin flip? |
| `always_a` / `always_b` | Position bias — published A/B cases skew toward B winning (publication bias) |
| `heuristic` | "The challenger usually wins" shortcut |
| `oneshot_gemini` | **The one that matters:** same model, same images, single prompt — isolates the value of the multi-agent panel itself |

The dataset uses **mirrored pairs** — every case appears twice with A/B swapped — so a method can't score above 50% by exploiting position or publication bias. On the balanced set, `always_a`, `always_b`, and `heuristic` all land at exactly 50%, which is the design working.

```bash
python validation/run.py --dataset validation/dataset_balanced.csv --baselines all
```

Predictions checkpoint after every case, so an interrupted run resumes instead of restarting; abstentions are re-attempted automatically.

### What the numbers say

On the 20-case balanced set (2026-06-11 run, free-tier Gemini under heavy 503 capacity pressure):

| Method | Accuracy | Decisive accuracy |
|---|---|---|
| `random` | 30.0% (6/20) | 30.0% (6/20) |
| `always_a` / `always_b` / `heuristic` | 50.0% (10/20) | 50.0% (10/20) |
| `oneshot_gemini` | 70.0% (14/20) | 70.0% (14/20) |
| **VeraTest (full pipeline)** | 45.0% (9/20, 10 abstained) | **90.0% (9/10)** |

- **When VeraTest committed to a verdict, it was right 9 of 10 (90%)** vs one-shot Gemini's 70% — small n, treat as a directional signal, not a benchmark claim.
- **One confident error in 20 cases.** One-shot Gemini, which always answers, was confidently wrong 6 times. Under degraded conditions VeraTest abstains ("tie") rather than fabricating a verdict — for a decision-support tool, refusing to guess *is* the correct behavior, and the pipeline now enforces it explicitly: if fewer than 70% of the persona panel completes (`SIMAB_SIM_QUORUM`), the run fails loudly instead of synthesizing from thin evidence.
- 10 of 20 runs degraded to abstention that day due to Gemini free-tier 503s — those score as *wrong* in the headline number (45%), which is why we report decisive accuracy separately and publish the raw per-case table in `validation/report_*.md` rather than a single flattering percentage.

Every report includes the full per-case prediction matrix, so you can audit exactly which cases each method got right.

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
