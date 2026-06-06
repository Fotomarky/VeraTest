# Results Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamline the run results page into four PM questions — add a PageSpeed-style persona hero, collapse the duplicated recommendation into one card, make user stories always coherent, and add an 80s-arcade typewriter overlay to the in-progress animation.

**Architecture:** Frontend-only changes to the Next.js results page (`frontend/app/runs/[id]/page.tsx`) and its components. Two new components (`ResultsHero`, `WhatToDoNext`) replace four render slots; `PersonaCard` is reused inside the hero; `SprintPriorities`, `TestNextHypothesis`, and `PersonaCarousel` are removed. No backend, model, or pipeline changes.

**Tech Stack:** Next.js 14 (App Router), React 18, TypeScript 5, Tailwind CSS. No JS test runner is configured in `frontend/`, so the per-task correctness gate is `npx tsc --noEmit` + `npm run build`; functional verification is a manual browser check in the final task (a real run consumes Gemini quota and takes minutes).

**Spec:** `docs/superpowers/specs/2026-06-07-results-page-redesign-design.md`

---

## File Structure

- **Create** `frontend/app/components/ResultsHero.tsx` — variant thumbnails + persona circles with lean rings, hover preview, click-to-expand (renders `PersonaCard`).
- **Create** `frontend/app/components/WhatToDoNext.tsx` — single card merging recommendation (was `TestNextHypothesis`) + top sprint fixes (was `SprintPriorities`).
- **Modify** `frontend/app/runs/[id]/page.tsx` — swap imports/renders to the new structure; fold `UserStoryScaffold` into a collapsible under `BlockersMatrix`; remove `PersonaCarousel`.
- **Modify** `frontend/app/components/UserStoryScaffold.tsx` — replace incoherent `themeToNeed()` regex with a verbatim-theme template.
- **Modify** `frontend/app/components/PackmanTheater.tsx` — draw typewriter "AGENTS ARE RUNNING" on the canvas.
- **Delete** `frontend/app/components/SprintPriorities.tsx`, `frontend/app/components/TestNextHypothesis.tsx`, `frontend/app/components/PersonaCarousel.tsx`.
- **Keep** `frontend/app/components/PersonaCard.tsx`, `BlockersMatrix.tsx`, `CommandRail.tsx`, `VisualEvidence.tsx` unchanged.

---

## Task 1: Make user stories always coherent

**Files:**
- Modify: `frontend/app/components/UserStoryScaffold.tsx`

- [ ] **Step 1: Delete the `NEGATIVE_TO_NEED` table and `themeToNeed()`**

Remove the entire block from the comment `// Map negative friction adjectives...` through the end of the `themeToNeed` function (the `const NEGATIVE_TO_NEED: Array<[RegExp, string]> = [ ... ];` array and the `export function themeToNeed(theme: string): string { ... }` function — currently lines ~26-90).

- [ ] **Step 2: Replace the friction-story template to keep the theme verbatim**

In the `highMed.map(...)` block, change the line that builds the need + text. Replace:

```tsx
          const persona = cleanPersona(findPrimaryPersona(t, resultsBySegment));
          const need = themeToNeed(t.theme);
          const text = `As a ${persona},\nI need ${need},\nso that I can ${goal}.`;
```

with:

```tsx
          const persona = cleanPersona(findPrimaryPersona(t, resultsBySegment));
          const text = `As a ${persona},\nI need ${t.theme} resolved,\nso that I can ${goal}.`;
```

The what-worked template (`✅ As a ${persona}, ${t.theme} supports ${goal} — ...`) is already coherent — leave it unchanged.

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (no errors; confirms no remaining references to `themeToNeed`).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/components/UserStoryScaffold.tsx
git commit -m "fix(user-stories): keep friction theme verbatim so stories are always coherent"
```

---

## Task 2: Combined "What to do next" card (removes duplicate recommendation)

**Files:**
- Create: `frontend/app/components/WhatToDoNext.tsx`
- Modify: `frontend/app/runs/[id]/page.tsx`
- Delete: `frontend/app/components/SprintPriorities.tsx`, `frontend/app/components/TestNextHypothesis.tsx`

- [ ] **Step 1: Create `WhatToDoNext.tsx`**

Create `frontend/app/components/WhatToDoNext.tsx` with this exact content:

```tsx
type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: Array<{ quote: string; agent_idx?: number | null; segment?: string | null }>;
  cohort?: "variant_a" | "variant_b" | "both";
};

type SimResult = {
  scenario_segment: string;
  cohort: "variant_a" | "variant_b";
};

type Props = {
  topFriction: FrictionTheme[];
  recommendation?: string;
  foggAvg: Record<string, Record<string, number>>;
  winner: string;
  simulationResults: SimResult[];
  confoundWarning?: string;
  totalAgents?: number;
  personaCount?: number;
};

const SEV_ICON: Record<string, string> = { high: "🔴", medium: "🟡", low: "🟢" };

function themeToAction(theme: string): string {
  const lower = theme.toLowerCase();
  if (/\bmissing\b/.test(lower) || /\black of\b/.test(lower)) {
    const stripped = theme.replace(/^(missing|lack of)\s*/i, "").trim();
    return stripped ? "Add " + stripped : theme;
  }
  if (/\bvague\b/.test(lower) || /\bunclear\b/.test(lower)) {
    const stripped = theme.replace(/^(vague|unclear)\s*/i, "").trim();
    return stripped ? "Clarify " + stripped : theme;
  }
  return theme;
}

function findTopSegment(simulationResults: SimResult[]): string {
  const counts: Record<string, number> = {};
  for (const r of simulationResults) {
    counts[r.scenario_segment] = (counts[r.scenario_segment] ?? 0) + 1;
  }
  const top = Object.entries(counts).sort(([, a], [, b]) => b - a)[0];
  return top ? top[0] : "your top segment";
}

export default function WhatToDoNext({
  topFriction,
  recommendation,
  foggAvg,
  winner,
  simulationResults,
  confoundWarning,
  totalAgents,
  personaCount,
}: Props) {
  const fixes = topFriction
    .filter((t) => t.severity === "high" || t.severity === "medium")
    .slice(0, 2);

  if (!recommendation && !fixes.length) return null;

  const winnerScores = foggAvg[winner] ?? foggAvg["variant_a"] ?? {};
  const currentAbility = winnerScores["ability"] ?? null;
  const abilityTarget =
    currentAbility !== null ? Math.min(10, Math.round(currentAbility + 2)) : 7;
  const topSegment = findTopSegment(simulationResults);

  return (
    <section className="rounded-lg border border-blue-100 bg-blue-50 p-5">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 className="font-semibold text-sm text-blue-900">What to do next</h2>
        <div className="flex items-center gap-1.5">
          {totalAgents != null && (
            <span className="text-[11px] px-2 py-0.5 rounded bg-white/70 text-blue-700 font-mono">
              {totalAgents} agents
            </span>
          )}
          {personaCount != null && (
            <span className="text-[11px] px-2 py-0.5 rounded bg-white/70 text-blue-700 font-mono">
              {personaCount} segment{personaCount !== 1 ? "s" : ""}
            </span>
          )}
          {confoundWarning && (
            <span className="text-[11px] text-orange-500" title={confoundWarning}>
              ⚠ directional
            </span>
          )}
        </div>
      </div>

      {recommendation && (
        <p className="text-sm text-blue-800 italic mb-3">&ldquo;{recommendation}&rdquo;</p>
      )}

      {fixes.length > 0 && (
        <ol className="space-y-2 mb-3">
          {fixes.map((t, i) => (
            <li key={i} className="flex items-start gap-3 text-sm">
              <span className="font-mono text-blue-400 text-xs mt-0.5 w-4 flex-shrink-0">
                {i + 1}.
              </span>
              <span className="flex-shrink-0">{SEV_ICON[t.severity] ?? "🟡"}</span>
              <span className="flex-1 text-blue-900">{themeToAction(t.theme)}</span>
              <span className="text-xs text-blue-400 flex-shrink-0">
                → {t.count} agent{t.count !== 1 ? "s" : ""}
              </span>
            </li>
          ))}
        </ol>
      )}

      <p className="text-xs text-blue-600">
        Expected signal: Ability score should rise above {abilityTarget} for {topSegment} in iteration 2.
      </p>
    </section>
  );
}
```

- [ ] **Step 2: Swap imports in `page.tsx`**

In `frontend/app/runs/[id]/page.tsx`, remove these two import lines:

```tsx
import SprintPriorities from "../../components/SprintPriorities";
import TestNextHypothesis from "../../components/TestNextHypothesis";
```

and add:

```tsx
import WhatToDoNext from "../../components/WhatToDoNext";
```

- [ ] **Step 3: Replace the SprintPriorities render block**

Replace this block (currently lines ~326-334):

```tsx
      {synth && (
        <SprintPriorities
          topFriction={synth.top_friction ?? []}
          recommendation={synth.recommendation}
          confoundWarning={synth.confound_warning}
          totalAgents={run.simulation_results?.length ?? total}
          personaCount={uniquePersonas.length}
        />
      )}
```

with:

```tsx
      {synth && (
        <WhatToDoNext
          topFriction={synth.top_friction ?? []}
          recommendation={synth.recommendation}
          foggAvg={foggAvg}
          winner={winner}
          simulationResults={run.simulation_results ?? []}
          confoundWarning={synth.confound_warning}
          totalAgents={run.simulation_results?.length ?? total}
          personaCount={uniquePersonas.length}
        />
      )}
```

- [ ] **Step 4: Remove the standalone TestNextHypothesis render block**

Delete this block entirely (currently lines ~366-373):

```tsx
      {synth?.recommendation && (
        <TestNextHypothesis
          recommendation={synth.recommendation}
          foggAvg={foggAvg}
          winner={winner}
          simulationResults={run.simulation_results ?? []}
        />
      )}
```

- [ ] **Step 5: Delete the two superseded component files**

```bash
git rm frontend/app/components/SprintPriorities.tsx frontend/app/components/TestNextHypothesis.tsx
```

- [ ] **Step 6: Type-check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: PASS, no references to the deleted components.

- [ ] **Step 7: Commit**

```bash
git add frontend/app/components/WhatToDoNext.tsx "frontend/app/runs/[id]/page.tsx"
git commit -m "feat(results): merge recommendation + sprint fixes into one What-to-do-next card"
```

---

## Task 3: Fold user stories into a collapsible under BlockersMatrix

**Files:**
- Modify: `frontend/app/runs/[id]/page.tsx`

- [ ] **Step 1: Remove the standalone UserStoryScaffold render**

In `frontend/app/runs/[id]/page.tsx`, delete this block (currently lines ~357-364):

```tsx
      {synth && (
        <UserStoryScaffold
          topFriction={synth.top_friction ?? []}
          whatWorkedThemes={synth.what_worked_themes ?? []}
          goal={run.goal}
          resultsBySegment={resultsBySegment}
        />
      )}
```

- [ ] **Step 2: Re-add it as a collapsible directly after the BlockersMatrix block**

Immediately after the closing `)}` of the `BlockersMatrix` render block (currently ends ~line 346), insert:

```tsx
      {synth && (
        <details className="rounded-lg border border-neutral-200 bg-white">
          <summary className="cursor-pointer px-5 py-3 text-sm font-semibold select-none">
            Copy to backlog — user stories
          </summary>
          <div className="px-5 pb-5">
            <UserStoryScaffold
              topFriction={synth.top_friction ?? []}
              whatWorkedThemes={synth.what_worked_themes ?? []}
              goal={run.goal}
              resultsBySegment={resultsBySegment}
            />
          </div>
        </details>
      )}
```

The `UserStoryScaffold` import at the top of the file stays (still used).

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add "frontend/app/runs/[id]/page.tsx"
git commit -m "feat(results): fold user stories into a collapsible under BlockersMatrix"
```

---

## Task 4: ResultsHero (variant thumbnails + persona circles) and remove PersonaCarousel

**Files:**
- Create: `frontend/app/components/ResultsHero.tsx`
- Modify: `frontend/app/runs/[id]/page.tsx`
- Delete: `frontend/app/components/PersonaCarousel.tsx`

- [ ] **Step 1: Create `ResultsHero.tsx`**

Create `frontend/app/components/ResultsHero.tsx` with this exact content:

```tsx
"use client";
import { useState } from "react";
import PersonaCard from "./PersonaCard";

type ScenarioCard = {
  id: string;
  segment: string;
  intent: string;
  decision_style: string;
  device: string;
  traffic_source: string;
  context: string;
  constraints: string[];
  time_pressure: string;
  price_sensitivity: string;
  traffic_weight: number;
  visual_style_preference?: string;
  patience_threshold?: string;
  communication_style?: string;
};

type SimResult = {
  scenario_id: string;
  scenario_segment: string;
  cohort: "variant_a" | "variant_b";
  resonance: Record<string, number>;
  resonance_overall: number;
  confidence: string;
  friction_points: string[];
  what_worked: string[];
  rationale: string;
  first_impression?: string;
  trust_signals_missing?: string[];
  metacognitive_reflection?: string;
};

type Props = {
  runId: string;
  personas: ScenarioCard[];
  resultsBySegment: Map<string, SimResult[]>;
  winner: "variant_a" | "variant_b" | "tie";
  isSingleScreen: boolean;
};

const STYLE_ICON: Record<string, string> = { analytical: "📊", impulse: "⚡", cautious: "🔍", social: "💬" };
const DEVICE_ICON: Record<string, string> = { desktop: "🖥", mobile: "📱", tablet: "📲" };

function cleanPersona(name: string): string {
  return name.replace(/^\s*(?:the|a|an)\s+/i, "").trim() || name;
}

function leanPercents(results: SimResult[]): { pctA: number; pctB: number } {
  const a = results.filter((r) => r.cohort === "variant_a").map((r) => r.resonance_overall);
  const b = results.filter((r) => r.cohort === "variant_b").map((r) => r.resonance_overall);
  const avgA = a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0;
  const avgB = b.length ? b.reduce((s, v) => s + v, 0) / b.length : 0;
  const total = avgA + avgB;
  if (total === 0) return { pctA: 50, pctB: 50 };
  const pctA = Math.round((avgA / total) * 100);
  return { pctA, pctB: 100 - pctA };
}

function avgOverall(results: SimResult[]): number {
  if (!results.length) return 0;
  return results.reduce((s, r) => s + r.resonance_overall, 0) / results.length;
}

function topFrictionPoint(results: SimResult[]): string | null {
  for (const r of results) {
    if (r.friction_points && r.friction_points.length) return r.friction_points[0];
  }
  return null;
}

export default function ResultsHero({ runId, personas, resultsBySegment, winner, isSingleScreen }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const sorted = [...personas].sort((a, b) => {
    const ac = resultsBySegment.get(a.segment)?.length ?? 0;
    const bc = resultsBySegment.get(b.segment)?.length ?? 0;
    return bc - ac;
  });

  const totalAgents = Array.from(resultsBySegment.values()).reduce((s, r) => s + r.length, 0);
  const selectedPersona = sorted.find((p) => p.segment === selected) ?? null;
  const selectedResults = selectedPersona ? resultsBySegment.get(selectedPersona.segment) ?? [] : [];

  return (
    <section>
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        <div className="grid grid-cols-[auto_1fr] gap-6 items-center max-sm:grid-cols-1">
          {/* Variant thumbnails */}
          <div className="flex gap-2">
            <Thumb runId={runId} which="a" label="A" win={winner === "variant_a"} />
            {!isSingleScreen && (
              <Thumb runId={runId} which="b" label="B" win={winner === "variant_b"} />
            )}
          </div>

          {/* Persona circles */}
          <div>
            <div className="text-[11px] uppercase tracking-wide text-neutral-400 mb-3">
              Who tested it · {totalAgents} agents across {sorted.length} persona{sorted.length !== 1 ? "s" : ""}
            </div>
            <div className="flex gap-5 flex-wrap">
              {sorted.map((p) => {
                const results = resultsBySegment.get(p.segment) ?? [];
                const count = results.length;
                let ring: string;
                let leanLabel: string;
                if (isSingleScreen) {
                  const pos = Math.max(0, Math.min(100, Math.round((avgOverall(results) / 10) * 100)));
                  ring = `conic-gradient(#22c55e 0 ${pos}%, #ef4444 ${pos}% 100%)`;
                  leanLabel = pos >= 60 ? "positive" : pos >= 40 ? "mixed" : "negative";
                } else {
                  const { pctA, pctB } = leanPercents(results);
                  ring = `conic-gradient(#3b82f6 0 ${pctA}%, #8b5cf6 ${pctA}% 100%)`;
                  leanLabel = Math.abs(pctA - pctB) <= 4 ? "split" : pctA > pctB ? "leans A" : "leans B";
                }
                const isActive = selected === p.segment;
                const tip = topFrictionPoint(results);
                return (
                  <button
                    key={p.segment}
                    onClick={() => setSelected(isActive ? null : p.segment)}
                    className="group relative flex flex-col items-center gap-1 w-24 text-center"
                  >
                    <div
                      className={`w-16 h-16 rounded-full p-1 transition-transform group-hover:scale-105 ${
                        isActive ? "ring-2 ring-blue-500" : ""
                      }`}
                      style={{ background: ring }}
                    >
                      <div className="w-full h-full rounded-full bg-white flex items-center justify-center text-xl">
                        {STYLE_ICON[p.decision_style] ?? DEVICE_ICON[p.device] ?? "🧑"}
                      </div>
                    </div>
                    <div className="text-[11px] font-semibold leading-tight line-clamp-2">
                      {cleanPersona(p.segment)}
                    </div>
                    <div className="text-[10px] text-neutral-400">
                      {count} agent{count !== 1 ? "s" : ""} · {leanLabel}
                      {isActive ? " ▾" : ""}
                    </div>

                    {/* hover tooltip preview */}
                    <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 rounded bg-neutral-800 text-white text-[10px] leading-snug px-2 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity shadow-lg z-20 text-left">
                      <span className="font-semibold block">{cleanPersona(p.segment)}</span>
                      <span className="text-neutral-300">
                        {count} agents · {leanLabel}
                      </span>
                      {tip && <span className="block text-neutral-300 mt-0.5">Top friction: {tip}</span>}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* legend */}
            <div className="flex gap-4 flex-wrap text-[10px] text-neutral-400 mt-3">
              {isSingleScreen ? (
                <>
                  <Legend color="#22c55e" label="positive" />
                  <Legend color="#ef4444" label="negative" />
                </>
              ) : (
                <>
                  <Legend color="#3b82f6" label="leans A" />
                  <Legend color="#8b5cf6" label="leans B" />
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* expanded persona detail */}
      {selectedPersona && (
        <div className="mt-3">
          <PersonaCard
            persona={selectedPersona}
            results={selectedResults}
            winner={winner}
            isSingleScreen={isSingleScreen}
          />
        </div>
      )}
    </section>
  );
}

function Thumb({
  runId,
  which,
  label,
  win,
}: {
  runId: string;
  which: "a" | "b";
  label: string;
  win: boolean;
}) {
  return (
    <div className="relative w-[84px] h-[120px] rounded-lg border border-neutral-200 overflow-hidden bg-neutral-100">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/runs/${runId}/image/${which}`}
        alt={`Variant ${label}`}
        className="w-full h-full object-cover"
      />
      <span className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-[10px] font-bold text-center py-0.5">
        {label}
        {win ? " ★" : ""}
      </span>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}
```

- [ ] **Step 2: Swap imports in `page.tsx`**

In `frontend/app/runs/[id]/page.tsx`, remove:

```tsx
import PersonaCarousel from "../../components/PersonaCarousel";
```

and add:

```tsx
import ResultsHero from "../../components/ResultsHero";
```

- [ ] **Step 3: Add the ResultsHero render directly after `<CommandRail .../>`**

The `CommandRail` render block ends at `/>` (currently ~line 303). Immediately after it, insert:

```tsx
      {synth && uniquePersonas.length > 0 && (
        <ResultsHero
          runId={run.run_id}
          personas={uniquePersonas}
          resultsBySegment={resultsBySegment}
          winner={winner}
          isSingleScreen={isSingleScreen}
        />
      )}
```

- [ ] **Step 4: Remove the PersonaCarousel render block**

Delete this block (currently lines ~348-355):

```tsx
      {uniquePersonas.length > 0 && (
        <PersonaCarousel
          personas={uniquePersonas}
          resultsBySegment={resultsBySegment}
          winner={winner}
          isSingleScreen={isSingleScreen}
        />
      )}
```

- [ ] **Step 5: Delete the PersonaCarousel file**

```bash
git rm frontend/app/components/PersonaCarousel.tsx
```

- [ ] **Step 6: Type-check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: PASS, no references to `PersonaCarousel`.

- [ ] **Step 7: Commit**

```bash
git add frontend/app/components/ResultsHero.tsx "frontend/app/runs/[id]/page.tsx"
git commit -m "feat(results): PageSpeed-style persona hero with lean rings + click-to-expand; drop carousel"
```

---

## Task 5: 80s-arcade typewriter overlay on PackmanTheater

**Files:**
- Modify: `frontend/app/components/PackmanTheater.tsx`

- [ ] **Step 1: Draw the typewriter text inside the render loop**

In `frontend/app/components/PackmanTheater.tsx`, find the vignette block that ends with `ctx.fillRect(0, 0, 640, 180);` (currently ~line 281). Immediately after that line and before the `if (countRef.current) {` block, insert:

```tsx
      // 80s-arcade typewriter caption drawn on top of the figures.
      const FULL_TEXT = "AGENTS ARE RUNNING";
      // ~7 frames per character reveal, hold the full string, then loop.
      const cycleLen = FULL_TEXT.length * 7 + 40;
      const phase = frame % cycleLen;
      const revealed = Math.min(FULL_TEXT.length, Math.floor(phase / 7));
      const shown = FULL_TEXT.slice(0, revealed);
      const cursorOn = Math.floor(frame / 16) % 2 === 0;
      const caption = shown + (revealed < FULL_TEXT.length || cursorOn ? "_" : " ");

      ctx.save();
      ctx.font = "bold 18px 'Courier New', monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      // dark drop-shadow for the neon-on-CRT look
      ctx.fillStyle = "rgba(0,0,0,0.7)";
      ctx.fillText(caption, 320 + 2, 14 + 2);
      // color-cycle the fill between arcade cyan and yellow
      ctx.fillStyle = Math.floor(frame / 20) % 2 === 0 ? "#22d3ee" : "#fde047";
      ctx.fillText(caption, 320, 14);
      ctx.restore();
```

- [ ] **Step 2: Simplify the now-redundant sub-caption (keep the counter)**

The numeric counter still lives below the canvas. Update the sub-caption text (currently `Agents doing their job… <span ref={countRef}>0 / 0</span>`) to just show the count, since "agents are running" now appears on-screen. Replace:

```tsx
      <p className="text-center text-xs text-neutral-400 mt-2 font-mono">
        Agents doing their job… <span ref={countRef}>0 / 0</span>
      </p>
```

with:

```tsx
      <p className="text-center text-xs text-neutral-400 mt-2 font-mono">
        <span ref={countRef}>0 / 0</span> agents
      </p>
```

- [ ] **Step 3: Type-check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: PASS. (Confirms `frame` is in scope at the insertion point — it is the same variable used by `drawAgent` for animation framing.)

- [ ] **Step 4: Commit**

```bash
git add frontend/app/components/PackmanTheater.tsx
git commit -m "feat(animation): 80s-arcade typewriter 'AGENTS ARE RUNNING' overlay on canvas"
```

---

## Task 6: Manual browser verification

**Files:** none (verification only)

- [ ] **Step 1: Start backend and frontend**

```bash
# Terminal 1 (repo root)
source .venv/bin/activate && export GEMINI_API_KEY="<key>" && uvicorn simab.main:app --reload --port 8000
# Terminal 2
cd frontend && npm run dev
```

- [ ] **Step 2: Trigger an A/B run**

```bash
python tests/fixtures/make_samples.py
curl -X POST http://localhost:8000/api/runs \
  -F "variant_a=@tests/fixtures/variant_a.png" \
  -F "variant_b=@tests/fixtures/variant_b.png" \
  -F "goal=sign up for free trial" \
  -F "audience=Startup founders evaluating CI tools"
```

Open `http://localhost:3000/runs/<run_id>`.

- [ ] **Step 3: Verify the in-progress state**

Expected: PackmanTheater canvas shows the typewriter "AGENTS ARE RUNNING" animating over the walking figures; the `N / M agents` counter updates below; SKIP ANIMATION still works.

- [ ] **Step 4: Verify the completed A/B state**

Expected, in order:
- Sticky `CommandRail` at top.
- `ResultsHero`: two variant thumbnails with a ★ on the winning variant; one circle per persona with blue/violet split rings sized by lean; hovering a circle shows the preview tooltip; clicking expands the `PersonaCard` inline below the hero; clicking again collapses it.
- `WhatToDoNext`: the recommendation appears **exactly once** on the page (grep the DOM/visual scan — it must NOT also appear in any other section); top fixes listed; "Expected signal" line present.
- `BlockersMatrix` unchanged.
- "Copy to backlog — user stories" collapsible under the matrix; expanding it shows coherent stories (e.g. "I need <theme> resolved").
- No PersonaCarousel anywhere.
- `VisualEvidence` at the bottom.

- [ ] **Step 5: Verify a single-screen run**

```bash
curl -X POST http://localhost:8000/api/runs \
  -F "variant_a=@tests/fixtures/variant_a.png" \
  -F "goal=sign up for free trial" \
  -F "audience=Startup founders evaluating CI tools"
```

Expected: hero shows one thumbnail, no ★; persona rings use the green/red positive-negative scheme with the positive/negative legend.

- [ ] **Step 6: Backend regression sanity**

Run: `pytest tests/ -v`
Expected: all pass (no backend changes were made; this just confirms nothing was disturbed).

---

## Self-Review Notes

- **Spec coverage:** new structure (Tasks 2-4), ResultsHero with hover+click and ring logic (Task 4), WhatToDoNext dedup (Task 2), coherent stories (Task 1), folded collapsible (Task 3), PersonaCarousel removal (Task 4), typewriter (Task 5), single-screen behavior (Task 4 ring branch + Task 6 verification). All covered.
- **Type consistency:** `WhatToDoNext` and `ResultsHero` prop names match the call sites added in `page.tsx`; `foggAvg`/`winner`/`simulationResults` are already computed in `page.tsx` (`computeFoggAvg`, `winner`, `run.simulation_results`). `PersonaCard` is invoked with its exact existing prop signature (`persona`, `results`, `winner`, `isSingleScreen`).
- **No backend/model changes:** confirmed; image URL `/api/runs/{id}/image/{which}` matches the existing pattern used by `VisualEvidence`.
