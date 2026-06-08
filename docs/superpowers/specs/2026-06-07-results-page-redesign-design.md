# Results Page Redesign — Streamlining & Persona Hero

**Date:** 2026-06-07
**Status:** Approved (design), pending implementation plan
**Scope:** `frontend/app/runs/[id]/page.tsx` + components; one small touch to `PackmanTheater.tsx`. No backend/model changes.

---

## Problem

A PM reviewing a run result page finds it "a bit overwhelming." Concrete issues:

1. **Friction shown three times** — `SprintPriorities`, `BlockersMatrix`, and `UserStoryScaffold` all re-render the same `top_friction` data, so the reader sees the same problems three ways with no clear hierarchy.
2. **Recommendation printed twice** — `SprintPriorities` appends `"Next hypothesis: {recommendation}"` AND `TestNextHypothesis` renders the same `recommendation` in a blue box.
3. **Incoherent user stories** — `UserStoryScaffold.themeToNeed()` inverts negative adjectives with regex, producing garbage like *"I need stronger information Overload & Usability of Diagnostic Data."*
4. **Unclear how agents are shown** — `PersonaCarousel` (one persona at a time behind arrows) doesn't make the panel composition glanceable; the reader can't see at a glance who tested it and how each segment leaned.
5. **No glanceable summary** — there is no PageSpeed-Insights-style "what was tested + headline metrics" band at the top.

## Goal / core purpose of the page

The page answers, in priority order: **(1) Did it win? (2) What do I do Monday? (3) Why? (4) Who said this?** The redesign reorganizes content into those four answers and removes redundancy.

---

## New page structure

Render order in `page.tsx` when `synthesis` is present (complete):

1. **Title** (unchanged) — goal + run id.
2. **CommandRail** (unchanged) — sticky verdict/validity/fidelity bar at `top-0`.
3. **ResultsHero** *(NEW)* — variant thumbnails + persona circles. The glanceable "what & who" band.
4. **WhatToDoNext** *(NEW, replaces SprintPriorities + TestNextHypothesis)* — single combined card: recommendation + top fixes.
5. **BlockersMatrix** (unchanged) — the diagnostic core, preserved exactly as-is.
6. **UserStoryScaffold** (folded) — rendered inside a collapsed `<details>` "Copy to backlog" directly under the matrix.
7. **VisualEvidence** (unchanged) — collapsible variant reference.

**Removed from the page:** `PersonaCarousel` (superseded by ResultsHero), the standalone `SprintPriorities` and `TestNextHypothesis` renders. `PersonaCard` is **kept** — reused inside ResultsHero's expanded detail panel.

In-progress and failed states are unchanged (`PackmanTheater` while running; red error block on fail), except for the PackmanTheater typewriter overlay below.

---

## Component: `ResultsHero` (new)

The above-the-fold summary, modeled on the PageSpeed Insights hero (metrics up top).

**Props:**
```ts
{
  runId: string;
  personas: ScenarioCard[];          // uniquePersonas from page.tsx
  resultsBySegment: Map<string, SimResult[]>;
  winner: "variant_a" | "variant_b" | "tie";
  isSingleScreen: boolean;
}
```

**Layout — two columns (stacks on mobile):**

- **Left — variant thumbnails.** `<img src="/api/runs/{runId}/image/a">`, and `/image/b` when not single-screen. Small (~84×120). A ★ marker on the winning variant (`winner === "variant_a"|"variant_b"`); no star on `tie` or single-screen.
- **Right — persona circles.** A header line: *"Who tested it · {N} agents across {M} personas"*. Then one circle per persona (sorted by agent count desc, same sort as the old carousel):
  - **Face:** persona icon (reuse `STYLE_ICON`/`DEVICE_ICON` from PersonaCard, or a default).
  - **Ring (conic-gradient):** encodes lean.
    - **A/B:** compute `{pctA, pctB}` for the persona's results via the existing `resonancePercents()` logic (avg `resonance_overall` per cohort → relative %). Ring = blue `0→pctA%`, violet `pctA%→100%`.
    - **Single-screen:** positive/negative. `pos% = clamp(avgResonanceOverall/10*100)`; ring = green `0→pos%`, red `pos%→100%`.
  - **Caption:** persona name (cleaned via existing `cleanPersona`) + *"{k} agents · leans A | leans B | split"* (split when `|pctA-pctB| ≤ 4`), or *"{k} agents · positive | mixed"* for single-screen.
  - **Legend** below the circles explaining the colors (blue=leans A, violet=leans B, green=positive, red=negative).

**Interactions (keep lightweight):**

- **Hover** a circle → CSS-only tooltip preview: persona name, agent count, resonance split (e.g. "7.2 (B) vs 5.1 (A)"), and the persona's top friction point. Pure CSS `:hover` (no JS state) where possible.
- **Click** a circle → toggles an **inline detail panel** rendered immediately below the hero. The panel is the existing `<PersonaCard persona=… results=… winner=… isSingleScreen=… />`. Clicking the same circle again collapses it; clicking another switches. Single `useState<string | null>(selectedSegment)`. This reuses PersonaCard verbatim, so the only net-new UI is the circles + toggle.

---

## Component: `WhatToDoNext` (new — replaces two components)

One card that merges the recommendation (was `TestNextHypothesis`) and the top sprint fixes (was `SprintPriorities`), eliminating the duplicate recommendation.

**Props:**
```ts
{
  topFriction: FrictionTheme[];
  recommendation?: string;
  foggAvg: Record<string, Record<string, number>>;
  winner: string;
  simulationResults: SimResult[];
  confoundWarning?: string;
  totalAgents?: number;
  personaCount?: number;
}
```

**Renders, in one bordered card titled "What to do next":**

1. The `recommendation` as an italic quote (the only place it appears on the page). Omit the block if no recommendation.
2. A numbered list of the top 2 high/medium friction fixes via the existing `themeToAction()` helper ("Add …", "Clarify …"), each with its agent count — carried over from SprintPriorities.
3. The "Expected signal" projection line carried over from TestNextHypothesis (ability-score target for the top segment).
4. The agents/segments chips + `⚠ directional` confound indicator carried over from the SprintPriorities header.

`themeToAction()` and the projection helper move into this component (or a shared util). `SprintPriorities.tsx` and `TestNextHypothesis.tsx` are deleted after their logic is absorbed.

---

## Fix: coherent user stories (`UserStoryScaffold`)

**Root cause:** `themeToNeed()` tries to invert an arbitrary friction noun-phrase into a positive "need" via regex substitution, which cannot guarantee grammaticality.

**Fix:** delete `themeToNeed()` and the `NEGATIVE_TO_NEED` table. Use a template that keeps the friction theme **verbatim** as the thing to resolve, which is always coherent regardless of theme wording:

> `As a {persona},`
> `I need {theme} resolved,`
> `so that I can {goal}.`

Example: *"As a Hands-on Builder, I need Information Overload & Poor Usability of Diagnostic Data resolved, so that I can sign up for free trial."* — coherent for any theme.

The what-worked template (`✅ As a {persona}, {theme} supports {goal} — preserve this…`) already reads coherently and is unchanged. `cleanPersona()` and `findPrimaryPersona()` are unchanged.

This component now lives inside a collapsed `<details>` under BlockersMatrix; its internal rendering is otherwise unchanged.

---

## Enhancement: 80s-arcade typewriter overlay (`PackmanTheater`)

Currently a static caption sits **below** the canvas: *"Agents doing their job… 0 / 0"*.

**Change:** draw arcade-style text **on the canvas, on top of the walking figures**, with a typewriter reveal of **"AGENTS ARE RUNNING"**:

- Drawn inside the existing `render()` rAF loop on the 640×180 canvas.
- Typewriter: reveal one character every ~120ms; after the full string holds briefly, reset and retype (loop) — or append an animated blinking cursor / ellipsis.
- 80s arcade styling: blocky/monospace uppercase, bright fill (e.g. cyan/yellow), optional 1px dark drop-shadow or per-character color cycling for the "neon" feel. Keep `imageRendering: pixelated` consistent with the existing art.
- Position: top-center of the canvas so it sits above the figures without obscuring the agent counter.
- The numeric `{completed} / {total}` counter stays (either as the existing sub-caption or folded into the canvas). The **SKIP ANIMATION** button is unchanged.

No new dependencies; all canvas 2D drawing.

---

## Single-screen behavior

- ResultsHero shows only the variant-A thumbnail, no ★; persona rings use the green/red positive-negative scheme; captions say "positive/mixed".
- WhatToDoNext, BlockersMatrix, UserStoryScaffold, VisualEvidence keep their existing single-screen handling.

## Data sources (no backend changes)

All values derive from data already on `Run`:
- Persona circles: `resultsBySegment` (agent counts), `resonance_overall` per cohort (lean), `top_friction`/per-result `friction_points` (tooltip).
- Thumbnails: existing `/api/runs/{id}/image/{a|b}` endpoint.
- Winner star: `synthesis.directional_winner`.

## Testing

- `cd frontend && npx tsc --noEmit` passes.
- Manual browser check (dev server) on:
  - An **A/B** run: hero shows two thumbnails with ★ on winner, persona rings split blue/violet, hover preview, click expands PersonaCard, recommendation appears exactly once, no PersonaCarousel.
  - A **single-screen** run: one thumbnail, green/red rings, no star.
  - **In-progress**: typewriter "AGENTS ARE RUNNING" animates over the figures; SKIP still works.
- `pytest tests/ -v` unaffected (no backend change) — run to confirm green.

## Out of scope

- No changes to `models.py`, pipeline, or any agent.
- No new persona-detail component (reuse PersonaCard).
- No LLM-generated user-story text (kept deterministic).
