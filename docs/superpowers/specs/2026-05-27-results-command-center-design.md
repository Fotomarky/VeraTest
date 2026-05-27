# Results Page: Command Center Redesign

**Date:** 2026-05-27  
**Status:** Approved for implementation  
**File:** `frontend/app/runs/[id]/page.tsx`

---

## Problem

The current results page is a vertical narrative report. A Product Manager or Product Owner must scroll through diagnostics, persona cards, Fogg scores, and trust gap sections before understanding what to build or fix. The priority hierarchy is inverted: images and winner summary appear first, actionable friction appears last.

The goal is to flip this into a **Command Center** — a page where a PM lands, reads 10 lines, knows what three tickets to write, and knows what to test next.

---

## Design Principles

1. **Validity → Verdict → Sprint Priorities → Blockers → Personas → User Stories → Evidence**
2. No information hidden by default except visual reference (collapsible)
3. Red / amber / green color coding is the primary navigation signal — not section headings
4. Every section either tells the PM what happened or what to do next — never both
5. User story scaffolding is the product's "winning positioning": SimAB surfaces the next sprint's backlog directly from A/B simulation data

---

## Page Layout (top → bottom)

```
┌─────────────────────────────────────────────────────────────┐
│ STICKY VERDICT RAIL                                          │
│ [⚠ Confound warning if any]  [Balance bar A←→B]  [Export]  │
└─────────────────────────────────────────────────────────────┘

  [ArcadeTheater — in-progress only, disappears on complete]

  SPRINT PRIORITIES
  1. 🔴 Add portfolio/social proof above the fold → 8 agents
  2. 🔴 Clarify CTA, remove premature email gate → 6 agents
  3. 💡 Next hypothesis: [synthesis.recommendation]

  CONVERSION BLOCKERS & WINS
  🔴  Missing portfolio proof   8 agents  Ability↓   ▼ quotes
  🔴  Vague CTA                 6 agents  Trigger↓   ▼ quotes
  🟡  Unclear value prop        4 agents  Motiv↓     ▼ quotes
  🟢  Strong headline           5 agents  Motiv↑     ▼ quotes
      Missing trust signals: [Portfolio] [Social proof]

  PERSONA CAROUSEL
  ◄  [PersonaCard — full detail, ordered by agent count]  ►
     • • ○ ○ ○   Persona 2 of 5 · 4 agents

  USER STORIES TO WRITE
  🔴 As a [Founder], I need portfolio proof so that…   [Copy]
  🟡 As a [SaaS PM], I need a clear CTA so that…      [Copy]
  🟢 Preserve: Strong headline works for [Founder]    [Copy]

  TEST THIS NEXT
  "If you apply the top 3 fixes, test this in iteration 2:
   [synthesis.recommendation]"
  Expected signal: Ability should rise above 7 for [top segment].

  VISUAL EVIDENCE  ▼ (collapsible, collapsed if confound_warning)
  [Variant A — large, subtle ring]  [Variant B — winner glow]
```

---

## Component Architecture

Seven new components. Existing components (`PersonaCard`, `FrictionList`, `VisualScores`) are kept and not deleted — `PersonaCard` is reused inside the carousel; the others remain available for the share page and exports.

| Component | File | Status | Replaces |
|---|---|---|---|
| `CommandRail` | `components/CommandRail.tsx` | New | Inline winner summary + variant images header |
| `SprintPriorities` | `components/SprintPriorities.tsx` | New | Nothing (new section) |
| `BlockersMatrix` | `components/BlockersMatrix.tsx` | New | `FrictionList` ×2 + trust signal gaps section |
| `PersonaCarousel` | `components/PersonaCarousel.tsx` | New | `PersonaCard` grid |
| `UserStoryScaffold` | `components/UserStoryScaffold.tsx` | New | Nothing (new section) |
| `TestNextHypothesis` | `components/TestNextHypothesis.tsx` | New | Nothing (new section) |
| `VisualEvidence` | `components/VisualEvidence.tsx` | New | Inline `VariantCard` + `VisualScores` |
| `page.tsx` | `app/runs/[id]/page.tsx` | Restructured | — |

---

## Component Specifications

### CommandRail

**Props:** `synthesis`, `audit`, `runId`, `status`  
**Behaviour:** sticky (`position: sticky; top: 0; z-index: 50`), ~64px tall.

Three horizontal zones:

**Left** — validity signal:
- If `synthesis.confound_warning` exists: amber strip `⚠ Test design issue — [short text]`. No box, just colored inline text.
- Else if `audit.trust_level !== "high"`: `⚠ Trust: MEDIUM` in amber.
- Else: empty / collapses.

**Center** — tug-of-war balance bar:
- Single horizontal bar split at `synthesis.weighted_vote` percentages.
- Left side blue (`bg-blue-500`), right side violet (`bg-violet-500`).
- A 2px white vertical needle marks the split point.
- Below the bar: `67%  ◄ VARIANT A WINS ►  33%` or `NO CLEAR WINNER` if `winner = "neither"` (bar is grey).
- During in-progress runs: shows `Simulating…` with a pulsing grey bar.

**Right** — metadata + actions:
- `coverage 84/100` badge.
- "Copy markdown" button and "Open share page" link (moved here from the title row).

---

### SprintPriorities

**Props:** `topFriction`, `recommendation`, `winner`  
**Behaviour:** A card immediately below the rail (or below ArcadeTheater during progress). Always the first content a PM reads on a completed run.

Renders a numbered list of up to 3 items:
- Items 1–2: top HIGH/MED friction themes from `synthesis.top_friction`, formatted as: `[severity icon] [theme rephrased as action verb phrase] → affects [count] agents`
- Item 3: `💡 Next hypothesis: [synthesis.recommendation]` if present, else the third friction item.

If the run has a `confound_warning`, the card shows a banner: `⚠ Test was confounded — treat these priorities as directional, not conclusive.`

Rephrasing friction themes as action verb phrases is done with a simple prefix map:
- Themes containing "missing" → "Add [theme]"
- Themes containing "vague" / "unclear" → "Clarify [theme]"
- Themes containing "lack" → "Include [theme]"
- Default: theme text as-is

---

### BlockersMatrix

**Props:** `topFriction`, `whatWorkedThemes`, `trustSignalGaps`, `foggAvg`, `winner`  
**Behaviour:** Unified sorted table replacing three separate sections.

**Sort order:** HIGH friction → MED friction → LOW friction → what-worked (green). Within each severity, sorted by `count` descending.

**Each row:**
- Left border color + background tint: red (high), amber (medium), green (low / what-worked)
- Severity dot + theme text (bold)
- Agent count badge: `8 agents`
- Fogg badge (derived from `foggAvg`):
  - If `foggAvg[winner].ability < 5` and theme relates to clarity/CTA → `Ability ↓`
  - If `foggAvg[winner].motivation < 5` → `Motiv ↓`
  - If `foggAvg[winner].motivation > 7` (for what-worked) → `Motiv ↑`
  - If none match: badge omitted
- Recommended fix hint: the highest-confidence `metacognitive_reflection` from simulation results matching that theme. Matching rule: split the friction theme string into words ≥5 characters, check if any word appears (case-insensitive) in the reflection string — use the first matching result's reflection. Shown as a `→ [hint text]` line in small text below the theme.
- Expand button `▼ quotes` → reveals `example_quotes`

**Trust signal gaps** rendered as a sub-group at the bottom of the red section: `Missing trust signals: [chip] [chip]`

---

### PersonaCarousel

**Props:** `personas` (ScenarioCard[]), `resultsBySegment` (Map), `winner`  
**Behaviour:** Single-card horizontal carousel.

**Ordering:** sorted by agent count descending (`resultsBySegment.get(segment).length`).

**Navigation:**
- Left/right arrow buttons on card edges
- Dot indicator strip below: filled dot = current, empty = others
- Header above card: `Persona 2 of 5 · 4 agents · [segment name]`

**Card header tint:**
- Green header strip: that persona's majority verdict matches overall winner
- Red header strip: that persona preferred the losing variant
- Amber header strip: split (pctA and pctB within 15% of each other)

Renders the existing `PersonaCard` component unchanged inside the carousel wrapper. No changes to `PersonaCard.tsx`.

---

### UserStoryScaffold

**Props:** `topFriction`, `whatWorkedThemes`, `goal`, `resultsBySegment`  
**Behaviour:** One card per HIGH/MED friction item + one card per HIGH "what worked" item.

**Template — blocker card:**
```
As a [primary persona],
I need [friction theme rephrased as a need],
so that [run.goal].
```

`[primary persona]` = the `scenario_segment` that appears most in the results associated with that theme (from `example_quotes` cross-referenced with `resultsBySegment`). Falls back to "a user" if unresolvable.

`[friction theme rephrased]` = same prefix-map logic as SprintPriorities, but as a noun phrase ("portfolio examples and designer proof").

**Template — what-worked card:**
```
✅ As a [persona], [what worked theme] supports [goal] —
   preserve this in the next iteration.
```

Each card:
- Severity color coding on left border
- "Copy" button: writes formatted text to clipboard
- Small metadata line: `Affects [count] agents · [Fogg badge if present]`

---

### TestNextHypothesis

**Props:** `recommendation`, `topFriction`, `foggAvg`, `winner`  
**Behaviour:** A single card below UserStoryScaffold.

Content:
- Heading: "Test This Next"
- Body: `"If you apply the top 3 fixes: [synthesis.recommendation]"`
- Expected signal line: `Expected: Ability score should rise above 7 for [top affected segment].` — derived from the top HIGH friction item's agent data.
- If `recommendation` is empty: omit the section entirely.

---

### VisualEvidence

**Props:** `runId`, `winner`, `visualImpact`, `confoundWarning?: string`  
**Behaviour:** Collapsible section, collapsed by default if `confoundWarning` is present.

- Two images side by side (`h-80`, `object-contain`, `bg-neutral-50`)
- No `border-2`. Winner: `ring-2 ring-emerald-300 shadow-md shadow-emerald-100`. Loser: `ring-1 ring-neutral-200`.
- Visual impact score badge: small chip overlaid bottom-right of each image (`7.2 / 10`)
- Winner chip: floating top-left (`winner` badge in emerald)
- Images link to `/api/runs/{runId}/image/{a|b}` (zoom on click, unchanged)
- `VisualScores` component is not rendered here — its data is embedded directly in the image badges

---

## Restructured page.tsx

```
<div className="space-y-5 max-w-4xl">
  <CommandRail ... />          {/* sticky */}

  {inProgress && <ArcadeTheater ... />}
  {failed && <ErrorBlock ... />}

  {synth && <SprintPriorities ... />}

  {synth && <BlockersMatrix ... />}

  {uniquePersonas.length > 0 && <PersonaCarousel ... />}

  {synth && <UserStoryScaffold ... />}

  {synth?.recommendation && <TestNextHypothesis ... />}

  <VisualEvidence ... />
</div>
```

The title row (`run.goal` + `run_id`) stays as a small heading above the rail — `run.goal` in `text-xl font-semibold`, `run_id` in `text-xs font-mono text-neutral-400`. Export buttons move into `CommandRail` right zone and are removed from the title row.

---

## Data Flow

All data comes from the existing `Run` object streamed via SSE. No new API endpoints required. No new backend changes. All new sections derive their content from fields already present in `synthesis`, `simulation_results`, `scenarios`, and `audit`.

The Fogg→friction linking is a pure frontend computation: compare `foggAvg[winner].ability` and `foggAvg[winner].motivation` thresholds against each blocker row to assign badges. No fuzzy matching — threshold rules only.

The user story persona attribution uses `resultsBySegment` (already computed in `page.tsx`) cross-referenced with `top_friction[i].example_quotes` — since quotes are strings, matching is done by checking if any quote appears in a result's `rationale` field for a given segment. Falls back gracefully to "a user" if no match found.

---

## What Is Not Changing

- ArcadeTheater in-progress animation — unchanged
- SSE streaming and immediate-fetch logic — unchanged
- Export functions (markdown copy, share page link) — moved to CommandRail, same logic
- `PersonaCard.tsx` — unchanged, reused inside PersonaCarousel
- `FrictionList.tsx` — kept, not rendered in main view, available for share page
- `VisualScores.tsx` — kept, not rendered in main view, available for share page
- Backend, API, models — no changes

---

## Success Criteria

A PM opening the completed results page should be able to:
1. Know within 5 seconds whether the test was valid and which variant won (CommandRail)
2. Know the top 3 sprint actions without scrolling (SprintPriorities)
3. Understand why each blocker matters via Fogg linkage (BlockersMatrix)
4. See which persona was most affected and read their verbatim reaction (PersonaCarousel)
5. Copy a ready-to-paste Jira user story in one click (UserStoryScaffold)
6. Know what hypothesis to test in the next iteration (TestNextHypothesis)
