# Junior Developer Task Briefs

Three self-contained tasks. Each can be done independently.

---

## Task 1 — CHANGELOG.md (30 min)

**What:** Write a `CHANGELOG.md` in the project root that summarizes what was built so far.

**Why it matters:** Hackathon judges check whether a project has momentum. A changelog signals "real product" not "weekend prototype."

**Format to use:** [Keep a Changelog](https://keepachangelog.com/) format.

**What to put in it:**

### [0.3.0] — 2026-05-29
#### Added
- Single-screen evaluation mode: `variant_b` is now optional. Upload one design to get resonance scoring, friction themes, and recommendations without an A/B comparison.
- Pixelated walking agent characters in the Packman loading theater (replaces Pac-Man circles). Each agent's jacket color matches its persona segment color.
- `PersonaCarousel` component — prev/next navigation through all persona diagnostics.
- `SprintPriorities` now shows agent count and segment count in the header instead of an alarming orange confound block.
- `UserStoryScaffold` — generates "As a … I need … so that I can …" cards from high/medium friction themes, with copy-to-clipboard.
- `TestNextHypothesis` — blue card surfacing the synthesis recommendation with an ability score target.
- Resonance reframe: 6-dimension scoring (motivation, identity, situation, beliefs, ability, trigger) replaces the 2-dimension Fogg model.
- CSS hover tooltips on all resonance dimension labels (replaces broken `title` attributes on Safari).
- Form validation: Variant A and goal fields show red highlight when submitting with empty fields.

#### Changed
- `BlockersMatrix` now unified into a single table showing both blockers and wins, with Fogg badges (Motiv↑↓, Ability↑↓) and recommended-fix hints.
- Results page restructured as "PM Command Center" with `CommandRail` sticky header.
- Animation restart bug fixed: agents no longer reset position on each SSE update.
- User story grammar fixed: "so that I can {goal}".

### [0.2.0] — (earlier)
#### Added
- Bias auditor agent — checks cohort balance, score inflation, rationale coherence.
- Structured audience preset chip selector on the /new form.
- Arize Phoenix OTLP observability integration.
- A2A (Google agent-to-agent) protocol endpoint.
- Markdown and HTML share page exports.

### [0.1.0] — initial
#### Added
- 5-agent pipeline: BriefNormalizer → ScenarioBuilder → 20×Simulator → BiasAuditor → Synthesizer.
- SQLite stigmergy state layer (pheromone trail pattern).
- Next.js 14 frontend with SSE live progress.
- MCP server with 4 tools.

---

## Task 2 — CI/CD `ci.yml` (2–3 hours)

**What:** Add `.github/workflows/ci.yml` that runs on every push and PR.

**Why it matters:** Judges check the repo. A green CI badge and a workflow file signal professional practice.

**What the workflow should do:**

```yaml
name: CI

on:
  push:
    branches: [main, feat/**]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install uv && uv pip install -e ".[dev]" --system
      - run: pytest tests/ -v
        env:
          GEMINI_API_KEY: "test-key-not-real"  # smoke tests don't call the API

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npx tsc --noEmit
        working-directory: frontend
```

**Important details:**
- The smoke tests at `tests/test_smoke.py` do NOT call the Gemini API — they test state, allocator, and schema only. They'll pass with a fake API key.
- Use `uv pip install --system` in GitHub Actions (no venv needed in CI).
- Frontend only needs type-check, not a full build (saves ~3 min per run).
- Do NOT add a deployment step — deploy is manual via `./gcp/deploy.sh`.

---

## Task 3 — README resonance reframe (1–2 hours)

**What:** Update the README to reframe VeraTest as a multi-mode platform, not just an A/B tool.

**Why it matters:** The tool now supports single-screen analysis. The README still says "upload two variants." That undersells it. Also: the hackathon track is "Google Cloud + Arize" — the README needs to surface both.

**Specific changes to make:**

### 1. Replace the headline section

Current:
```
20 AI agents simulate your audience. They evaluate your landing page variants like real people do...
```

New version should say something like:
```
20 AI agents simulate your target audience evaluating your landing page design — before you spend a cent on traffic.

Upload one design for friction analysis. Upload two to find the directional winner.
```

### 2. Add a "Three modes" section after "How it works"

```markdown
## Three evaluation modes

| Mode | What you upload | What you get |
|---|---|---|
| **Single design** | One screenshot | Resonance score, friction themes, trust gaps, sprint stories |
| **A/B pretest** | Two variants | All of the above + directional winner with gap significance |
| **N-variant** *(roadmap)* | 3+ variants | Ranked resonance matrix |

Start with a single design analysis — it's the fastest way to understand your audience before you build variant B.
```

### 3. Add a badges row for Google Cloud and Arize near the top

Add these to the existing badge row:
```
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Arize Phoenix](https://img.shields.io/badge/Arize-Phoenix%20Observability-7C3AED?style=for-the-badge)
```

### 4. Update the "The problem with A/B testing" section title

Change it to: `## The problem with guessing about your design`

And update the first paragraph to mention single-design analysis as the first use case.

### 5. Don't change anything else — keep all technical documentation as-is.
