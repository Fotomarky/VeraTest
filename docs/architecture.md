# VeraTest — System Architecture

## Production topology (Google Cloud Run)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Platform                        │
│                         Project: veratest-497813                    │
│                                                                     │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐  │
│  │   Cloud Run: frontend    │    │   Cloud Run: backend          │  │
│  │   veratest-frontend      │    │   veratest-backend            │  │
│  │   node:20-alpine         │    │   python:3.11-slim            │  │
│  │   Next.js 14 standalone  │───▶│   FastAPI + uvicorn           │  │
│  │   Port 3000 · 512Mi      │    │   Port 8000 · 2Gi · 2CPU      │  │
│  │   0–5 instances          │    │   1–3 instances · 600s TO     │  │
│  └──────────────────────────┘    └──────────┬───────────────────┘  │
│                                             │                       │
│                                  ┌──────────▼───────────────────┐  │
│                                  │   Secret Manager              │  │
│                                  │   gemini-api-key (v1)         │  │
│                                  └──────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐  │
│  │   Container Registry     │    │   Cloud Storage (auto)        │  │
│  │   veratest-backend:latest│    │   veratest-497813_cloudbuild  │  │
│  │   veratest-frontend:latest    │   Build source archives        │  │
│  └──────────────────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

External services called by backend:
  Google Gemini API  (aistudio.google.com)
  Arize Phoenix      (optional OTLP — localhost:4317 in local dev)
```

**Live URLs**
- Frontend: `https://veratest-frontend-169174549586.us-central1.run.app`
- Backend:  `https://veratest-backend-169174549586.us-central1.run.app`
- Health:   `/health` → `{"status":"ok","version":"0.1.0"}`

---

## Agent pipeline (stigmergy / pheromone trail)

All agents communicate exclusively through a shared SQLite document (`Run`). No agent receives parameters from another agent directly. Each reads its input slice and writes its output slice — like ants leaving and reading pheromone trails.

```
                         ┌─────────────────────────────────────────────────────────────┐
                         │                   SQLite (WAL mode)                         │
                         │   Run document — the shared pheromone trail                 │
 Input                   │                                                             │
 ──────                  │  goal  audience  variant_a_path  variant_b_path             │
 variant_a (image)  ────▶│                                           ↓                 │
 variant_b (image)  ────▶│  ┌─────────────────────────────────────────────────────┐   │
 goal               ────▶│  │  Phase 1: BriefNormalizer  (gemini-2.5-flash)       │   │
 audience preset    ────▶│  │  Reads: goal, audience, images                      │   │
                         │  │  Writes: run.brief (personas, summaries, diffs)     │   │
                         │  └────────────────────┬────────────────────────────────┘   │
                         │                       ↓                                    │
                         │  ┌─────────────────────────────────────────────────────┐   │
                         │  │  Phase 2: ScenarioBuilder  (gemini-2.5-flash)       │   │
                         │  │  Reads: run.brief.inferred_personas                 │   │
                         │  │  Writes: run.scenarios (20 micro-varied cards)      │   │
                         │  │          run.agent_allocations                      │   │
                         │  └────────────────────┬────────────────────────────────┘   │
                         │                       ↓  fan-out (SIMAB_SIM_CONCURRENCY=6) │
                         │  ┌─────────────────────────────────────────────────────┐   │
                         │  │  Phase 3: 20 × SimAgent  (gemini-2.5-flash-lite)    │   │
                         │  │  Each reads: run.scenarios[i], ONE variant image    │   │
                         │  │  A/B mode:  agent_idx % 2 → cohort assignment       │   │
                         │  │  Single:    all agents evaluate variant_a           │   │
                         │  │  Writes: run.simulation_results[i] (idempotent)     │   │
                         │  └────────────────────┬────────────────────────────────┘   │
                         │                       ↓                                    │
                         │  ┌─────────────────────────────────────────────────────┐   │
                         │  │  Phase 4: BiasAuditor  (gemini-2.5-flash)           │   │
                         │  │  Reads: run.simulation_results                      │   │
                         │  │  Checks: cohort balance, score inflation,           │   │
                         │  │          rationale coherence, dim variance          │   │
                         │  │  Writes: run.audit  (trust_level, warnings)         │   │
                         │  └────────────────────┬────────────────────────────────┘   │
                         │                       ↓                                    │
                         │  ┌─────────────────────────────────────────────────────┐   │
                         │  │  Phase 5: Synthesizer  (gemini-2.5-flash)           │   │
                         │  │  Reads: run.simulation_results, run.audit           │   │
                         │  │  Clusters friction + what-worked themes             │   │
                         │  │  A/B: computes gap, verdict, significance           │   │
                         │  │  Single: resonance summary, no gap                  │   │
                         │  │  Writes: run.synthesis, sets status=synthesizing    │   │
                         │  └────────────────────┬────────────────────────────────┘   │
                         │                       ↓  parallel (3 sub-agents)           │
                         │  ┌─────────────────────────────────────────────────────┐   │
                         │  │  Phase 6: NarrativeAgents  (gemini-2.5-flash)       │   │
                         │  │  3 sub-agents run in parallel:                      │   │
                         │  │  • structural_diff    — factual design diffs        │   │
                         │  │  • symmetric_hypothesis — 3 pros + 3 cons each      │   │
                         │  │  • cohort_narrative    — score-based story          │   │
                         │  │  Writes: run.synthesis.{structural_diff,            │   │
                         │  │          hypothesis_pros/cons, narrative}           │   │
                         │  │  Sets status=complete                               │   │
                         │  └─────────────────────────────────────────────────────┘   │
                         └─────────────────────────────────────────────────────────────┘
```

---

## Evaluation modes

```
Single-screen mode              A/B comparison mode
──────────────────              ───────────────────
Upload 1 image                  Upload 2 images

All 20 agents → variant_a       Agents 0,2,4… → variant_a  (cohort A)
cohort = "variant_a" always     Agents 1,3,5… → variant_b  (cohort B)

No gap calculation              gap = mean(B) - mean(A)
directional_winner = "tie"      _verdict() → winner + significance
CommandRail: resonance bar      CommandRail: A vs B tug-of-war
PersonaCard: no vote bar        PersonaCard: resonance vote bar
```

---

## Frontend data flow

```
Browser
  │
  ├── SSE /api/runs/{id}/stream ──▶ setRun(data) on each update
  │
  └── page.tsx (runs/[id])
        │
        ├── computeFoggAvg(results)    ← derives per-cohort resonance from SimResult[]
        ├── isSingleScreen = !run.variant_b_path
        │
        ├── <CommandRail>              sticky header, verdict / resonance bar
        ├── <PackmanTheater>           canvas animation while in-flight
        ├── <SprintPriorities>         top 3 friction as sprint tasks
        ├── <BlockersMatrix>           friction + wins table, Fogg badges
        ├── <PersonaCarousel>          carousel of PersonaCard per segment
        │     └── <PersonaCard>        6-dim resonance bars, trust gaps, vote bar
        ├── <UserStoryScaffold>        "As a … I need … so that I can …" cards
        ├── <TestNextHypothesis>       recommendation + ability target
        └── <VisualEvidence>           collapsible variant images
```

---

## LLM model assignment

```
Agent                  Model                     Why
─────────────────────  ────────────────────────  ──────────────────────────────────────
BriefNormalizer        gemini-2.5-flash          Needs vision + structured extraction
ScenarioBuilder        gemini-2.5-flash          Context variation, JSON array output
20 × SimAgent          gemini-2.5-flash-lite     Volume (20 calls) — free tier 1500/day
BiasAuditor            gemini-2.5-flash          Coherence scoring (LLM-as-judge)
Synthesizer            gemini-2.5-flash          Theme clustering, summary prose
NarrativeAgents (×3)   gemini-2.5-flash          Parallel; no image for cohort_narrative
```

---

## Storage schema (SQLite)

```sql
runs (
  run_id TEXT PK,
  status TEXT,                  -- pending|normalizing|building_scenarios|
                                --   simulating|auditing|synthesizing|complete|failed
  goal TEXT,
  audience_raw TEXT,
  audience_preset_json TEXT,    -- NULL if not provided
  persona_source TEXT,
  variant_a_path TEXT,
  variant_b_path TEXT,          -- "" for single-screen runs
  brief_json TEXT,
  scenarios_json TEXT,
  agent_allocations_json TEXT,
  audit_json TEXT,
  synthesis_json TEXT,
  error TEXT
)

sim_results (
  run_id TEXT,
  scenario_id TEXT,
  agent_idx INTEGER,
  result_json TEXT,             -- serialised SimResult
  PRIMARY KEY (run_id, scenario_id, agent_idx)  ← idempotent mutex
)
```

---

## Deployment — re-deploy after changes

```bash
# Backend only
gcloud builds submit --tag gcr.io/veratest-497813/veratest-backend:latest --project veratest-497813
gcloud run deploy veratest-backend --image gcr.io/veratest-497813/veratest-backend:latest \
  --region us-central1 --project veratest-497813

# Frontend only
gcloud builds submit /path/to/frontend --config /path/to/frontend/cloudbuild.yaml --project veratest-497813
gcloud run deploy veratest-frontend --image gcr.io/veratest-497813/veratest-frontend:latest \
  --region us-central1 --project veratest-497813

# Or use the script (builds + deploys both):
./gcp/deploy.sh veratest-497813
```
