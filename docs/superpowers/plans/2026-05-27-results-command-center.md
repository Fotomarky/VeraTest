# Results Page Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `frontend/app/runs/[id]/page.tsx` into a PM Command Center — sticky verdict rail, sprint priorities, unified blockers matrix, persona carousel, user story scaffold, and collapsible visual evidence — without touching the backend or existing component logic.

**Architecture:** Seven new presentational components wrap/replace existing sections; `page.tsx` is restructured to render them in the new priority order (Validity → Verdict → Sprint Priorities → Blockers → Personas → User Stories → Evidence). All data comes from the existing SSE-streamed `Run` object — no API changes. Existing `PersonaCard`, `FrictionList`, and `VisualScores` are kept but no longer rendered in the main view.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind CSS. Verification: `cd frontend && npx tsc --noEmit`. Visual verification in browser at `http://localhost:3000`.

---

## File Map

| File | Action |
|---|---|
| `frontend/app/components/CommandRail.tsx` | Create |
| `frontend/app/components/SprintPriorities.tsx` | Create |
| `frontend/app/components/BlockersMatrix.tsx` | Create |
| `frontend/app/components/PersonaCarousel.tsx` | Create |
| `frontend/app/components/UserStoryScaffold.tsx` | Create |
| `frontend/app/components/TestNextHypothesis.tsx` | Create |
| `frontend/app/components/VisualEvidence.tsx` | Create |
| `frontend/app/runs/[id]/page.tsx` | Restructure |
| `frontend/app/components/PersonaCard.tsx` | Unchanged — reused inside PersonaCarousel |
| `frontend/app/components/FrictionList.tsx` | Unchanged — kept for share page |
| `frontend/app/components/VisualScores.tsx` | Unchanged — kept for share page |
| `frontend/app/components/ArcadeTheater.tsx` | Unchanged |

---

## Task 1: CommandRail

**Files:**
- Create: `frontend/app/components/CommandRail.tsx`

The sticky rail that appears at the top of the viewport on scroll. Three horizontal zones: validity warning (left), tug-of-war balance bar (center), metadata + export actions (right).

- [ ] **Step 1: Create the file**

```tsx
"use client";

type SynthesisForRail = {
  winner: string;
  weighted_vote: Record<string, number>;
  coverage_score: number;
  confound_warning?: string;
};

type AuditForRail = {
  trust_level: string;
  recommended_action: string;
};

type Props = {
  synthesis: SynthesisForRail | null;
  audit: AuditForRail | null;
  runId: string;
  status: string;
  onCopyMarkdown: () => void;
  copied: boolean;
};

export default function CommandRail({
  synthesis,
  audit,
  runId,
  status,
  onCopyMarkdown,
  copied,
}: Props) {
  const winner = synthesis?.winner ?? "neither";
  const voteA = Math.round((synthesis?.weighted_vote?.["variant_a"] ?? 0) * 100);
  const voteB = Math.round((synthesis?.weighted_vote?.["variant_b"] ?? 0) * 100);
  const isComplete = status === "complete";
  const inProgress = !isComplete && status !== "failed";

  const confoundWarning = synthesis?.confound_warning;
  const trustIssue =
    audit?.trust_level && audit.trust_level !== "high" ? audit.trust_level : null;

  return (
    <div className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-neutral-200 px-4 py-2">
      <div className="flex items-center gap-4 max-w-4xl mx-auto">

        {/* Left: validity */}
        <div className="flex-shrink-0 w-44">
          {confoundWarning ? (
            <span className="text-xs text-orange-600 font-medium">⚠ Test design issue</span>
          ) : trustIssue ? (
            <span className="text-xs text-amber-600 font-medium">
              ⚠ Trust: {trustIssue.toUpperCase()}
            </span>
          ) : isComplete ? (
            <span className="text-xs text-emerald-600 font-medium">✓ Valid test</span>
          ) : (
            <span className="text-xs text-neutral-400">Analysing…</span>
          )}
        </div>

        {/* Center: balance bar */}
        <div className="flex-1 min-w-0">
          {inProgress ? (
            <div className="space-y-1">
              <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
                <div className="h-full bg-neutral-300 rounded-full animate-pulse w-1/3" />
              </div>
              <p className="text-[10px] text-neutral-400 text-center">Simulating…</p>
            </div>
          ) : isComplete ? (
            <div className="space-y-1">
              <div className="relative h-2 rounded-full overflow-hidden flex">
                <div
                  className={`h-full transition-all ${
                    winner === "neither" ? "bg-neutral-300" : "bg-blue-500"
                  }`}
                  style={{ width: `${winner === "neither" ? 50 : voteA}%` }}
                />
                <div
                  className={`h-full transition-all ${
                    winner === "neither" ? "bg-neutral-300" : "bg-violet-500"
                  }`}
                  style={{ width: `${winner === "neither" ? 50 : voteB}%` }}
                />
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-white"
                  style={{ left: `${winner === "neither" ? 50 : voteA}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px]">
                <span
                  className={
                    winner === "variant_a"
                      ? "text-blue-600 font-semibold"
                      : "text-neutral-400"
                  }
                >
                  A {voteA}%
                </span>
                <span
                  className={`font-medium ${
                    winner === "neither"
                      ? "text-neutral-500"
                      : winner === "variant_a"
                      ? "text-blue-600"
                      : "text-violet-600"
                  }`}
                >
                  {winner === "neither"
                    ? "NO CLEAR WINNER"
                    : winner === "variant_a"
                    ? "◄ VARIANT A WINS"
                    : "VARIANT B WINS ►"}
                </span>
                <span
                  className={
                    winner === "variant_b"
                      ? "text-violet-600 font-semibold"
                      : "text-neutral-400"
                  }
                >
                  {voteB}% B
                </span>
              </div>
            </div>
          ) : null}
        </div>

        {/* Right: coverage + actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {synthesis?.coverage_score != null && (
            <span className="text-[10px] text-neutral-400">
              coverage {synthesis.coverage_score}/100
            </span>
          )}
          {isComplete && (
            <>
              <button
                onClick={onCopyMarkdown}
                className="px-3 py-1 text-[10px] rounded border border-neutral-300 hover:bg-neutral-50"
              >
                {copied ? "✓ Copied" : "Copy MD"}
              </button>
              <a
                href={`/share/${runId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1 text-[10px] rounded bg-neutral-900 text-white hover:bg-neutral-700"
              >
                Share
              </a>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no errors for `CommandRail.tsx`. (Other pre-existing errors in the project are acceptable — only new errors matter.)

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/CommandRail.tsx
git commit -m "feat: add CommandRail sticky verdict + balance bar component"
```

---

## Task 2: SprintPriorities

**Files:**
- Create: `frontend/app/components/SprintPriorities.tsx`

A numbered 3-item card showing the top sprint actions. Items 1–2 come from the top HIGH/MED friction themes, rephrased as action verb phrases. Item 3 is the `synthesis.recommendation` hypothesis (or the third friction item if recommendation is absent).

- [ ] **Step 1: Create the file**

```tsx
type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: string[];
};

type Props = {
  topFriction: FrictionTheme[];
  recommendation?: string;
  confoundWarning?: string;
};

function themeToAction(theme: string): string {
  const lower = theme.toLowerCase();
  if (lower.includes("missing") || lower.includes("lack of")) {
    return "Add " + theme.replace(/^missing\s*/i, "").replace(/^lack of\s*/i, "");
  }
  if (lower.includes("vague") || lower.includes("unclear")) {
    return "Clarify " + theme.replace(/^vague\s*/i, "").replace(/^unclear\s*/i, "");
  }
  return theme;
}

const SEV_ICON: Record<string, string> = { high: "🔴", medium: "🟡", low: "🟢" };

export default function SprintPriorities({
  topFriction,
  recommendation,
  confoundWarning,
}: Props) {
  const highMed = topFriction
    .filter((t) => t.severity === "high" || t.severity === "medium")
    .slice(0, 2);

  const items: Array<{ icon: string; text: string; agents?: number }> = highMed.map((t) => ({
    icon: SEV_ICON[t.severity] ?? "🟡",
    text: themeToAction(t.theme),
    agents: t.count,
  }));

  if (recommendation) {
    items.push({ icon: "💡", text: `Next hypothesis: ${recommendation}` });
  } else if (topFriction[2]) {
    const t = topFriction[2];
    items.push({
      icon: SEV_ICON[t.severity] ?? "🟡",
      text: themeToAction(t.theme),
      agents: t.count,
    });
  }

  if (!items.length) return null;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <h2 className="font-semibold text-sm mb-3">Sprint Priorities</h2>
      {confoundWarning && (
        <p className="text-xs text-orange-600 bg-orange-50 rounded px-3 py-2 mb-3">
          ⚠ Test was confounded — treat these priorities as directional, not conclusive.
        </p>
      )}
      <ol className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3 text-sm">
            <span className="font-mono text-neutral-400 text-xs mt-0.5 w-4 flex-shrink-0">
              {i + 1}.
            </span>
            <span className="flex-shrink-0">{item.icon}</span>
            <span className="flex-1 text-neutral-800">{item.text}</span>
            {item.agents != null && (
              <span className="text-xs text-neutral-400 flex-shrink-0">
                → {item.agents} agent{item.agents !== 1 ? "s" : ""}
              </span>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/SprintPriorities.tsx
git commit -m "feat: add SprintPriorities top-3 actions card"
```

---

## Task 3: BlockersMatrix

**Files:**
- Create: `frontend/app/components/BlockersMatrix.tsx`

Unified table replacing the two `FrictionList` sections and the trust signal gaps section. Rows sorted HIGH → MED → LOW → what-worked. Each row has a Fogg badge derived from `fogg_avg` thresholds and a recommended-fix hint from `metacognitive_reflection` keyword matching.

- [ ] **Step 1: Create the file**

```tsx
"use client";
import { useState } from "react";

type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: string[];
};

type SimResult = {
  scenario_segment: string;
  verdict: string;
  confidence: string;
  outcome: string;
  rationale: string;
  friction_points: string[];
  what_worked: string[];
  metacognitive_reflection?: string;
  fogg_motivation?: number;
  fogg_ability?: number;
};

type Props = {
  topFriction: FrictionTheme[];
  whatWorkedThemes: FrictionTheme[];
  trustSignalGaps: string[];
  foggAvg: Record<string, Record<string, number>>;
  winner: string;
  simulationResults: SimResult[];
};

function getFoggBadge(
  foggAvg: Record<string, Record<string, number>>,
  winner: string,
  theme: FrictionTheme,
  isWorked: boolean
): string | null {
  const scores = foggAvg[winner] ?? foggAvg["variant_a"] ?? {};
  const motivation = scores["motivation"] ?? 10;
  const ability = scores["ability"] ?? 10;
  const lower = theme.theme.toLowerCase();
  if (isWorked) {
    if (motivation > 7) return "Motiv ↑";
    if (ability > 7) return "Ability ↑";
    return null;
  }
  const ctaRelated =
    lower.includes("cta") ||
    lower.includes("call to action") ||
    lower.includes("unclear") ||
    lower.includes("vague") ||
    lower.includes("gate");
  if (ctaRelated && ability < 5) return "Ability ↓";
  if (ability < 5) return "Ability ↓";
  if (motivation < 5) return "Motiv ↓";
  return null;
}

function getRecommendedFix(theme: FrictionTheme, results: SimResult[]): string | null {
  const words = theme.theme
    .split(/\s+/)
    .filter((w) => w.length >= 5)
    .map((w) => w.toLowerCase());
  for (const r of results) {
    if (!r.metacognitive_reflection) continue;
    const ref = r.metacognitive_reflection.toLowerCase();
    if (words.some((w) => ref.includes(w))) {
      const reflection = r.metacognitive_reflection;
      return reflection.length > 120 ? reflection.slice(0, 117) + "…" : reflection;
    }
  }
  return null;
}

const SEV_STYLES: Record<
  string,
  { border: string; bg: string; dot: string }
> = {
  high:   { border: "border-l-red-400",   bg: "bg-red-50",   dot: "bg-red-400"   },
  medium: { border: "border-l-amber-400", bg: "bg-amber-50", dot: "bg-amber-400" },
  low:    { border: "border-l-green-400", bg: "bg-green-50", dot: "bg-green-400" },
  worked: { border: "border-l-green-500", bg: "bg-green-50", dot: "bg-green-500" },
};

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

export default function BlockersMatrix({
  topFriction,
  whatWorkedThemes,
  trustSignalGaps,
  foggAvg,
  winner,
  simulationResults,
}: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const sortedFriction = [...topFriction].sort(
    (a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3) ||
      b.count - a.count
  );

  const rows = [
    ...sortedFriction.map((t) => ({ theme: t, isWorked: false })),
    ...whatWorkedThemes.map((t) => ({ theme: t, isWorked: true })),
  ];

  if (!rows.length && !trustSignalGaps.length) return null;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-semibold text-sm">Conversion Blockers & Wins</h2>
        <span className="text-xs text-neutral-400">
          {sortedFriction.length} blocker{sortedFriction.length !== 1 ? "s" : ""} ·{" "}
          {whatWorkedThemes.length} working
        </span>
      </div>

      <div className="space-y-2">
        {rows.map(({ theme: t, isWorked }) => {
          const sev = isWorked ? SEV_STYLES.worked : (SEV_STYLES[t.severity] ?? SEV_STYLES.medium);
          const foggBadge = getFoggBadge(foggAvg, winner, t, isWorked);
          const fix = !isWorked ? getRecommendedFix(t, simulationResults) : null;
          const key = `${isWorked ? "w" : "f"}-${t.theme}`;
          const isOpen = expanded === key;
          const hasQuotes = t.example_quotes && t.example_quotes.length > 0;

          return (
            <div
              key={key}
              className={`border-l-2 ${sev.border} ${sev.bg} pl-3 pr-3 py-2 rounded-r`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${sev.dot}`} />
                    <span className="text-sm font-medium">{t.theme}</span>
                    <span className="text-[10px] text-neutral-500">
                      {t.count} agent{t.count !== 1 ? "s" : ""}
                    </span>
                    {foggBadge && (
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${
                          foggBadge.includes("↑")
                            ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                            : "bg-red-50 border-red-200 text-red-700"
                        }`}
                      >
                        {foggBadge}
                      </span>
                    )}
                  </div>
                  {fix && (
                    <p className="text-xs text-neutral-500 mt-1 italic">→ {fix}</p>
                  )}
                </div>
                {hasQuotes && (
                  <button
                    onClick={() => setExpanded(isOpen ? null : key)}
                    className="text-[10px] text-neutral-500 hover:text-neutral-800 shrink-0 whitespace-nowrap mt-0.5"
                  >
                    {isOpen ? "▲ hide" : "▼ quotes"}
                  </button>
                )}
              </div>
              {isOpen && hasQuotes && (
                <div className="mt-2 space-y-1">
                  {t.example_quotes.map((q, j) => (
                    <p key={j} className="text-xs text-neutral-600 italic">
                      &ldquo;{q}&rdquo;
                    </p>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* Trust signal gaps sub-row */}
        {trustSignalGaps.length > 0 && (
          <div className="border-l-2 border-l-red-300 bg-red-50 pl-3 pr-3 py-2 rounded-r">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] text-red-700 font-medium">
                Missing trust signals:
              </span>
              {trustSignalGaps.map((gap, i) => (
                <span
                  key={i}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-white border border-red-200 text-red-700 font-medium"
                >
                  {gap}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/BlockersMatrix.tsx
git commit -m "feat: add BlockersMatrix unified blockers + wins table with Fogg badges"
```

---

## Task 4: PersonaCarousel

**Files:**
- Create: `frontend/app/components/PersonaCarousel.tsx`

Wraps the existing `PersonaCard` in a single-card horizontal carousel. Personas sorted by agent count descending. Verdict tint shown as a 4px colored top strip above the card (green = preferred winner, red = preferred loser, amber = split).

- [ ] **Step 1: Create the file**

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
  verdict: string;
  confidence: string;
  outcome: string;
  rationale: string;
  visual_impact?: Record<string, number>;
  attention_path?: string[];
  messaging_alignment?: string;
  first_impression?: string;
  friction_points: string[];
  what_worked: string[];
  fogg_motivation?: number;
  fogg_ability?: number;
  fogg_trigger_clarity?: string;
  trust_signals_missing?: string[];
  loss_gain_framing?: string;
};

type Props = {
  personas: ScenarioCard[];
  resultsBySegment: Map<string, SimResult[]>;
  winner: string;
};

type VerdictTint = "winner" | "loser" | "split";

function getVerdictTint(results: SimResult[], winner: string): VerdictTint {
  if (!results.length) return "split";
  const pctA = results.filter((r) => r.verdict === "variant_a").length / results.length;
  const pctB = results.filter((r) => r.verdict === "variant_b").length / results.length;
  if (Math.abs(pctA - pctB) <= 0.15) return "split";
  const preferred = pctA > pctB ? "variant_a" : "variant_b";
  return preferred === winner ? "winner" : "loser";
}

const TINT_STRIP: Record<VerdictTint, string> = {
  winner: "bg-emerald-400",
  loser: "bg-red-400",
  split: "bg-amber-400",
};

const TINT_RING: Record<VerdictTint, string> = {
  winner: "ring-emerald-200",
  loser: "ring-red-200",
  split: "ring-amber-200",
};

export default function PersonaCarousel({ personas, resultsBySegment, winner }: Props) {
  const sorted = [...personas].sort((a, b) => {
    const aCount = resultsBySegment.get(a.segment)?.length ?? 0;
    const bCount = resultsBySegment.get(b.segment)?.length ?? 0;
    return bCount - aCount;
  });

  const [index, setIndex] = useState(0);

  if (!sorted.length) return null;

  const current = sorted[index];
  const results = resultsBySegment.get(current.segment) ?? [];
  const tint = getVerdictTint(results, winner);

  return (
    <section>
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <h2 className="font-semibold text-sm">
          Persona Diagnostics
          <span className="text-neutral-400 font-normal ml-2">
            ({sorted.length} segment{sorted.length !== 1 ? "s" : ""})
          </span>
        </h2>
        <span className="text-xs text-neutral-500">
          Persona {index + 1} of {sorted.length} · {results.length} agent
          {results.length !== 1 ? "s" : ""} · {current.segment}
        </span>
      </div>

      <div className="relative px-5">
        {/* Prev arrow */}
        {sorted.length > 1 && (
          <button
            onClick={() => setIndex((i) => (i - 1 + sorted.length) % sorted.length)}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-white border border-neutral-200 shadow-sm hover:bg-neutral-50 text-neutral-500"
            aria-label="Previous persona"
          >
            ‹
          </button>
        )}

        {/* Card with verdict tint strip */}
        <div className={`rounded-lg overflow-hidden ring-1 ${TINT_RING[tint]}`}>
          <div className={`h-1 ${TINT_STRIP[tint]}`} />
          <PersonaCard persona={current} results={results} winner={winner} />
        </div>

        {/* Next arrow */}
        {sorted.length > 1 && (
          <button
            onClick={() => setIndex((i) => (i + 1) % sorted.length)}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-white border border-neutral-200 shadow-sm hover:bg-neutral-50 text-neutral-500"
            aria-label="Next persona"
          >
            ›
          </button>
        )}
      </div>

      {/* Dot indicators */}
      {sorted.length > 1 && (
        <div className="flex justify-center gap-1.5 mt-3">
          {sorted.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === index ? "w-3 bg-neutral-700" : "w-1.5 bg-neutral-300"
              }`}
              aria-label={`Go to persona ${i + 1}`}
            />
          ))}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/PersonaCarousel.tsx
git commit -m "feat: add PersonaCarousel sorted by agent count with verdict tint"
```

---

## Task 5: UserStoryScaffold

**Files:**
- Create: `frontend/app/components/UserStoryScaffold.tsx`

Generates copy-ready user story cards from friction data. One card per HIGH/MED friction item, one per HIGH what-worked item. Primary persona is derived by checking which segment's results contain keywords from the friction theme in their friction_points.

- [ ] **Step 1: Create the file**

```tsx
"use client";
import { useState } from "react";

type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: string[];
};

type SimResult = {
  scenario_segment: string;
  rationale: string;
  friction_points: string[];
  what_worked: string[];
};

type Props = {
  topFriction: FrictionTheme[];
  whatWorkedThemes: FrictionTheme[];
  goal: string;
  resultsBySegment: Map<string, SimResult[]>;
};

function themeToNeed(theme: string): string {
  const lower = theme.toLowerCase();
  if (lower.includes("missing") || lower.includes("lack of")) {
    return theme.replace(/^missing\s*/i, "").replace(/^lack of\s*/i, "").trim();
  }
  if (lower.includes("vague") || lower.includes("unclear")) {
    return (
      "a clearer " +
      theme.replace(/^vague\s*/i, "").replace(/^unclear\s*/i, "").trim()
    );
  }
  return theme;
}

function findPrimaryPersona(
  theme: FrictionTheme,
  resultsBySegment: Map<string, SimResult[]>
): string {
  const words = theme.theme
    .split(/\s+/)
    .filter((w) => w.length >= 5)
    .map((w) => w.toLowerCase());

  const segmentCounts: Record<string, number> = {};

  for (const [segment, results] of resultsBySegment) {
    for (const r of results) {
      const inFriction = r.friction_points.some((fp) =>
        words.some((w) => fp.toLowerCase().includes(w))
      );
      const inRationale =
        words.length > 0 && words.some((w) => r.rationale.toLowerCase().includes(w));
      if (inFriction || inRationale) {
        segmentCounts[segment] = (segmentCounts[segment] ?? 0) + 1;
      }
    }
  }

  const top = Object.entries(segmentCounts).sort(([, a], [, b]) => b - a)[0];
  return top ? top[0] : "a user";
}

const SEV_BORDER: Record<string, string> = {
  high: "border-l-red-400",
  medium: "border-l-amber-400",
  low: "border-l-green-400",
};

export default function UserStoryScaffold({
  topFriction,
  whatWorkedThemes,
  goal,
  resultsBySegment,
}: Props) {
  const [copied, setCopied] = useState<string | null>(null);

  const highMed = topFriction.filter(
    (t) => t.severity === "high" || t.severity === "medium"
  );
  const topWorked = whatWorkedThemes
    .filter((t) => t.severity === "high" || t.severity === "medium")
    .slice(0, 2);

  if (!highMed.length && !topWorked.length) return null;

  async function copyText(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    } catch {}
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="mb-3">
        <h2 className="font-semibold text-sm">User Stories to Write</h2>
        <p className="text-xs text-neutral-400 mt-0.5">
          Generated from simulation findings — copy directly to your backlog.
        </p>
      </div>
      <div className="space-y-3">
        {highMed.map((t, i) => {
          const persona = findPrimaryPersona(t, resultsBySegment);
          const need = themeToNeed(t.theme);
          const text = `As a ${persona},\nI need ${need},\nso that ${goal}.`;
          const key = `friction-${i}`;
          return (
            <div
              key={key}
              className={`border-l-2 ${
                SEV_BORDER[t.severity] ?? "border-l-neutral-300"
              } pl-3 pr-3 py-2 rounded-r bg-neutral-50`}
            >
              <pre className="text-xs text-neutral-700 font-sans whitespace-pre-wrap leading-relaxed">
                {text}
              </pre>
              <div className="flex items-center justify-between mt-2">
                <span className="text-[10px] text-neutral-400">
                  Affects {t.count} agent{t.count !== 1 ? "s" : ""}
                </span>
                <button
                  onClick={() => copyText(text, key)}
                  className="text-[10px] px-2 py-0.5 rounded border border-neutral-300 hover:bg-white text-neutral-600"
                >
                  {copied === key ? "✓ Copied" : "Copy"}
                </button>
              </div>
            </div>
          );
        })}

        {topWorked.map((t, i) => {
          const persona = findPrimaryPersona(t, resultsBySegment);
          const text = `✅ As a ${persona}, ${t.theme} supports ${goal} —\n   preserve this in the next iteration.`;
          const key = `worked-${i}`;
          return (
            <div
              key={key}
              className="border-l-2 border-l-green-400 pl-3 pr-3 py-2 rounded-r bg-green-50"
            >
              <pre className="text-xs text-neutral-700 font-sans whitespace-pre-wrap leading-relaxed">
                {text}
              </pre>
              <div className="flex items-center justify-between mt-2">
                <span className="text-[10px] text-neutral-400">
                  Affects {t.count} agent{t.count !== 1 ? "s" : ""}
                </span>
                <button
                  onClick={() => copyText(text, key)}
                  className="text-[10px] px-2 py-0.5 rounded border border-neutral-300 hover:bg-white text-neutral-600"
                >
                  {copied === key ? "✓ Copied" : "Copy"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/UserStoryScaffold.tsx
git commit -m "feat: add UserStoryScaffold with copy-to-clipboard backlog cards"
```

---

## Task 6: TestNextHypothesis

**Files:**
- Create: `frontend/app/components/TestNextHypothesis.tsx`

A single blue card showing the synthesis recommendation as the next iteration hypothesis. Includes an expected signal line derived from the current Fogg ability score + top affected segment.

- [ ] **Step 1: Create the file**

```tsx
type SimResult = {
  scenario_segment: string;
  verdict: string;
};

type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: string[];
};

type Props = {
  recommendation: string;
  topFriction: FrictionTheme[];
  foggAvg: Record<string, Record<string, number>>;
  winner: string;
  simulationResults: SimResult[];
};

function findTopSegment(simulationResults: SimResult[]): string {
  const counts: Record<string, number> = {};
  for (const r of simulationResults) {
    counts[r.scenario_segment] = (counts[r.scenario_segment] ?? 0) + 1;
  }
  const top = Object.entries(counts).sort(([, a], [, b]) => b - a)[0];
  return top ? top[0] : "your top segment";
}

export default function TestNextHypothesis({
  recommendation,
  foggAvg,
  winner,
  simulationResults,
}: Props) {
  if (!recommendation) return null;

  const winnerScores = foggAvg[winner] ?? foggAvg["variant_a"] ?? {};
  const currentAbility = winnerScores["ability"] ?? null;
  const abilityTarget =
    currentAbility !== null ? Math.min(10, Math.round(currentAbility + 2)) : 7;
  const topSegment = findTopSegment(simulationResults);

  return (
    <section className="rounded-lg border border-blue-100 bg-blue-50 p-5">
      <h2 className="font-semibold text-sm text-blue-900 mb-2">Test This Next</h2>
      <p className="text-sm text-blue-800 italic mb-3">
        &ldquo;{recommendation}&rdquo;
      </p>
      <p className="text-xs text-blue-600">
        Expected signal: Ability score should rise above {abilityTarget} for{" "}
        {topSegment} in iteration 2.
      </p>
    </section>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/TestNextHypothesis.tsx
git commit -m "feat: add TestNextHypothesis next iteration hypothesis card"
```

---

## Task 7: VisualEvidence

**Files:**
- Create: `frontend/app/components/VisualEvidence.tsx`

Collapsible section with both variant images displayed large. Replaces the inline `VariantCard` function and `VisualScores` component. No `border-2` boxes — winner gets an emerald ring + shadow, loser gets a neutral ring. Visual score overlaid as a bottom-right badge.

- [ ] **Step 1: Create the file**

```tsx
"use client";
import { useState } from "react";

type Props = {
  runId: string;
  winner: string;
  visualImpact: Record<string, number>;
  confoundWarning?: string;
};

export default function VisualEvidence({
  runId,
  winner,
  visualImpact,
  confoundWarning,
}: Props) {
  const [open, setOpen] = useState(!confoundWarning);

  const scoreA = visualImpact?.["variant_a"] ?? 0;
  const scoreB = visualImpact?.["variant_b"] ?? 0;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-neutral-50"
      >
        <h2 className="font-semibold text-sm">Visual Reference</h2>
        <span className="text-xs text-neutral-400">{open ? "▲ hide" : "▼ show"}</span>
      </button>

      {open && (
        <div className="px-5 pb-5">
          {confoundWarning && (
            <p className="text-xs text-orange-600 mb-3">
              Test was confounded — use for reference only.
            </p>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {(["a", "b"] as const).map((which) => {
              const isWinner = winner === `variant_${which}`;
              const score = which === "a" ? scoreA : scoreB;
              return (
                <div key={which}>
                  <div className="text-xs font-medium text-neutral-600 mb-1">
                    Variant {which.toUpperCase()}
                  </div>
                  <a
                    href={`/api/runs/${runId}/image/${which}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <div
                      className={`relative rounded overflow-hidden ${
                        isWinner
                          ? "ring-2 ring-emerald-300 shadow-md shadow-emerald-100"
                          : "ring-1 ring-neutral-200"
                      }`}
                    >
                      <img
                        src={`/api/runs/${runId}/image/${which}`}
                        alt={`Variant ${which.toUpperCase()}`}
                        className="w-full h-80 object-contain bg-neutral-50 hover:opacity-90 transition cursor-zoom-in"
                      />
                      {score > 0 && (
                        <span className="absolute bottom-2 right-2 text-[10px] bg-black/60 text-white px-1.5 py-0.5 rounded font-medium">
                          {score}/10
                        </span>
                      )}
                      {isWinner && (
                        <span className="absolute top-2 left-2 text-[10px] bg-emerald-500 text-white px-2 py-0.5 rounded font-medium">
                          winner
                        </span>
                      )}
                    </div>
                  </a>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/VisualEvidence.tsx
git commit -m "feat: add VisualEvidence collapsible image section with score badges"
```

---

## Task 8: Restructure page.tsx

**Files:**
- Modify: `frontend/app/runs/[id]/page.tsx`

Replace the old layout with the new Command Center order. Import all seven new components. Remove the inline `VariantCard` function (replaced by `VisualEvidence`). Keep `ProgressBlock` in place — it's still used as the `fallback` prop for `ArcadeTheater`. Remove the old confound warning block, trust banner, winner section, `VisualScores`, persona grid, `FrictionList` sections, Fogg section, trust gaps section, and all-agent-voices section — all replaced by the new components.

- [ ] **Step 1: Rewrite page.tsx**

Replace the entire file content with:

```tsx
"use client";
import { useEffect, useState } from "react";
import ArcadeTheater from "../../components/ArcadeTheater";
import CommandRail from "../../components/CommandRail";
import SprintPriorities from "../../components/SprintPriorities";
import BlockersMatrix from "../../components/BlockersMatrix";
import PersonaCarousel from "../../components/PersonaCarousel";
import UserStoryScaffold from "../../components/UserStoryScaffold";
import TestNextHypothesis from "../../components/TestNextHypothesis";
import VisualEvidence from "../../components/VisualEvidence";

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
  verdict: string;
  confidence: string;
  outcome: string;
  rationale: string;
  visual_impact?: Record<string, number>;
  attention_path?: string[];
  messaging_alignment?: string;
  first_impression?: string;
  friction_points: string[];
  what_worked: string[];
  fogg_motivation?: number;
  fogg_ability?: number;
  fogg_trigger_clarity?: string;
  trust_signals_missing?: string[];
  loss_gain_framing?: string;
  metacognitive_reflection?: string;
};

type Run = {
  run_id: string;
  status: string;
  goal: string;
  scenarios?: ScenarioCard[];
  simulation_results?: SimResult[];
  audit?: { trust_level: string; warnings: string[]; recommended_action: string };
  synthesis?: {
    winner: string;
    weighted_vote: Record<string, number>;
    coverage_score: number;
    top_friction: Array<{
      theme: string;
      count: number;
      severity: "high" | "medium" | "low";
      example_quotes: string[];
    }>;
    what_worked_themes: Array<{
      theme: string;
      count: number;
      severity: "high" | "medium" | "low";
      example_quotes: string[];
    }>;
    one_line_summary?: string;
    recommendation?: string;
    visual_impact?: Record<string, number>;
    confound_warning?: string;
    fogg_avg?: Record<string, Record<string, number>>;
    trust_signal_gaps?: string[];
  };
  error?: string;
};

const PHASE_LABELS: Record<string, string> = {
  pending: "Queued — waiting for the orchestrator",
  normalizing: "Reading the brief — analysing variants and extracting personas",
  building_scenarios: "Building scenarios — assigning agents proportionally to traffic",
  simulating: "Running simulation agents in parallel",
  auditing: "Auditing — checking for bias and confidence collapse",
  synthesizing: "Synthesising final report — clustering friction themes",
  complete: "Complete",
  failed: "Failed",
};

const PHASE_ORDER = [
  "pending",
  "normalizing",
  "building_scenarios",
  "simulating",
  "auditing",
  "synthesizing",
] as const;

const PHASE_SHORT: Record<string, string> = {
  pending: "Queued",
  normalizing: "Brief",
  building_scenarios: "Scenarios",
  simulating: "Simulate",
  auditing: "Audit",
  synthesizing: "Synthesise",
};

function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m > 0 ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

export default function RunPage({ params }: { params: { id: string } }) {
  const [run, setRun] = useState<Run | null>(null);
  const [copied, setCopied] = useState(false);
  const [mountedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/runs/${params.id}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data) setRun(data);
      })
      .catch(() => {});

    const source = new EventSource(`/api/runs/${params.id}/stream`);
    source.addEventListener("update", (e: MessageEvent) => {
      try {
        setRun(JSON.parse(e.data));
      } catch {}
    });
    source.onerror = () => {
      fetch(`/api/runs/${params.id}`)
        .then((r) => r.json())
        .then(setRun)
        .catch(() => {});
      source.close();
    };
    return () => {
      cancelled = true;
      source.close();
    };
  }, [params.id]);

  useEffect(() => {
    if (run?.status === "complete" || run?.status === "failed") return;
    const i = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(i);
  }, [run]);

  async function copyMarkdown() {
    try {
      const r = await fetch(`/api/runs/${params.id}/export.md`);
      const text = await r.text();
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  if (!run) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div>
          <h1 className="text-xl font-semibold">Connecting…</h1>
          <div className="text-xs font-mono text-neutral-400 mt-1">{params.id}</div>
        </div>
        <CommandRail
          synthesis={null}
          audit={null}
          runId={params.id}
          status="pending"
          onCopyMarkdown={copyMarkdown}
          copied={copied}
        />
      </div>
    );
  }

  const completed = run.simulation_results?.length ?? 0;
  const total = run.scenarios?.length ?? 20;
  const inProgress = run.status !== "complete" && run.status !== "failed";
  const synth = run.synthesis;
  const winner = synth?.winner ?? "neither";

  const scenariosBySegment = new Map<string, ScenarioCard>();
  for (const sc of run.scenarios ?? []) {
    if (!scenariosBySegment.has(sc.segment)) scenariosBySegment.set(sc.segment, sc);
  }
  const uniquePersonas = Array.from(scenariosBySegment.values());

  const resultsBySegment = new Map<string, SimResult[]>();
  for (const r of run.simulation_results ?? []) {
    const bucket = resultsBySegment.get(r.scenario_segment) ?? [];
    bucket.push(r);
    resultsBySegment.set(r.scenario_segment, bucket);
  }

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Title */}
      <div className="min-w-0">
        <h1 className="text-xl font-semibold truncate">{run.goal}</h1>
        <div className="text-xs font-mono text-neutral-400 mt-1">{run.run_id}</div>
      </div>

      <CommandRail
        synthesis={synth ?? null}
        audit={run.audit ?? null}
        runId={run.run_id}
        status={run.status}
        onCopyMarkdown={copyMarkdown}
        copied={copied}
      />

      {inProgress && (
        <ArcadeTheater
          run={run}
          fallback={
            <ProgressBlock
              status={run.status}
              completed={completed}
              total={total}
              elapsedMs={now - mountedAt}
            />
          }
        />
      )}

      {run.status === "failed" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="font-medium mb-1">Run failed</div>
          <div className="text-xs font-mono break-all">{run.error ?? "unknown error"}</div>
        </div>
      )}

      {synth && (
        <SprintPriorities
          topFriction={synth.top_friction ?? []}
          recommendation={synth.recommendation}
          confoundWarning={synth.confound_warning}
        />
      )}

      {synth && (
        <BlockersMatrix
          topFriction={synth.top_friction ?? []}
          whatWorkedThemes={synth.what_worked_themes ?? []}
          trustSignalGaps={synth.trust_signal_gaps ?? []}
          foggAvg={synth.fogg_avg ?? {}}
          winner={winner}
          simulationResults={run.simulation_results ?? []}
        />
      )}

      {uniquePersonas.length > 0 && (
        <PersonaCarousel
          personas={uniquePersonas}
          resultsBySegment={resultsBySegment}
          winner={winner}
        />
      )}

      {synth && (
        <UserStoryScaffold
          topFriction={synth.top_friction ?? []}
          whatWorkedThemes={synth.what_worked_themes ?? []}
          goal={run.goal}
          resultsBySegment={resultsBySegment}
        />
      )}

      {synth?.recommendation && (
        <TestNextHypothesis
          recommendation={synth.recommendation}
          topFriction={synth.top_friction ?? []}
          foggAvg={synth.fogg_avg ?? {}}
          winner={winner}
          simulationResults={run.simulation_results ?? []}
        />
      )}

      <VisualEvidence
        runId={run.run_id}
        winner={winner}
        visualImpact={synth?.visual_impact ?? {}}
        confoundWarning={synth?.confound_warning}
      />
    </div>
  );
}

function ProgressBlock({
  status,
  completed,
  total,
  elapsedMs,
}: {
  status: string;
  completed: number;
  total: number;
  elapsedMs: number;
}) {
  const currentIdx = PHASE_ORDER.indexOf(status as (typeof PHASE_ORDER)[number]);
  const phaseLabel = PHASE_LABELS[status] ?? status;
  const isSimulating = status === "simulating";
  const phaseNum = currentIdx >= 0 ? currentIdx + 1 : 0;
  const phaseTotal = PHASE_ORDER.length;
  const overallPct = (() => {
    if (currentIdx < 0) return 5;
    if (isSimulating && total > 0) {
      const base = (PHASE_ORDER.indexOf("simulating") / phaseTotal) * 100;
      const slice = (1 / phaseTotal) * 100;
      return base + slice * Math.min(1, completed / total);
    }
    return ((currentIdx + 0.5) / phaseTotal) * 100;
  })();

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 space-y-3">
      <div className="flex items-center justify-between text-sm gap-3 flex-wrap">
        <span className="font-medium">{phaseLabel}</span>
        <span className="text-neutral-600 text-xs flex items-center gap-3">
          {phaseNum > 0 && (
            <span>
              Phase <span className="font-mono">{phaseNum}/{phaseTotal}</span>
            </span>
          )}
          {isSimulating && (
            <span className="font-mono">
              {completed} / {total} agents
            </span>
          )}
          <span className="font-mono text-neutral-500">{formatElapsed(elapsedMs)}</span>
        </span>
      </div>
      <div className="h-1.5 bg-neutral-200 rounded-full overflow-hidden">
        <div
          className={`h-full bg-amber-500 transition-all ${isSimulating ? "" : "animate-pulse"}`}
          style={{ width: `${overallPct}%` }}
        />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {PHASE_ORDER.map((p, i) => {
          const isPast = i < currentIdx;
          const isCurrent = i === currentIdx;
          return (
            <span
              key={p}
              className={[
                "text-[11px] px-2 py-0.5 rounded-full border font-medium",
                isCurrent && "bg-amber-500 text-white border-amber-500",
                isPast && "bg-neutral-200 text-neutral-600 border-neutral-200",
                !isCurrent && !isPast && "bg-white text-neutral-400 border-neutral-200",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {isPast ? "✓ " : ""}
              {PHASE_SHORT[p] ?? p}
            </span>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npx tsc --noEmit
```

Expected: no errors. If there are type errors on `resultsBySegment` passed to `PersonaCarousel` or `UserStoryScaffold`, it is because TypeScript's Map type is invariant — cast the map: `resultsBySegment as Map<string, any[]>` only as a last resort; first try adjusting the component prop types to match the full `SimResult` type defined in `page.tsx`.

- [ ] **Step 3: Start the dev server and verify visually**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npm run dev
```

Open `http://localhost:3000`. Navigate to an existing completed run. Verify:
- Sticky rail appears and stays visible when scrolling
- Balance bar shows the correct A/B split
- Sprint Priorities card appears as the first content section
- Blockers Matrix shows red/amber/green rows with Fogg badges
- Persona Carousel shows one card at a time with prev/next arrows and dots
- User Stories section shows copy-ready cards
- Test This Next card appears in blue
- Visual Evidence is collapsed (if confound_warning) or open

- [ ] **Step 4: Commit**

```bash
git add frontend/app/runs/[id]/page.tsx
git commit -m "feat: restructure results page as PM Command Center

Seven new components replace the old narrative report layout.
Priority order: verdict rail → sprint priorities → blockers →
persona carousel → user stories → next hypothesis → visual evidence.
No backend changes."
```

---

## Self-Review Checklist

- [x] CommandRail: sticky rail, balance bar, validity text, export buttons — covered in Task 1
- [x] SprintPriorities: 3-item list, confound banner, themeToAction prefix map — covered in Task 2
- [x] BlockersMatrix: sort order, Fogg badges, fix hints, trust gaps, expandable quotes — covered in Task 3
- [x] PersonaCarousel: sort by agent count, verdict tint strip, arrows, dot indicators — covered in Task 4
- [x] UserStoryScaffold: friction + what-worked templates, primary persona attribution, copy button — covered in Task 5
- [x] TestNextHypothesis: recommendation card, Fogg ability target, top segment — covered in Task 6
- [x] VisualEvidence: collapsible, larger images, ring styles, score badges, winner chip — covered in Task 7
- [x] page.tsx restructure: new import list, new layout order, title row above rail, ProgressBlock kept — covered in Task 8
- [x] Existing components (PersonaCard, FrictionList, VisualScores, ArcadeTheater) left untouched
- [x] No backend changes anywhere in the plan
