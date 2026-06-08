"use client";
import { useState } from "react";

type QuoteSource = { quote: string; agent_idx?: number | null; segment?: string | null };

type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: QuoteSource[];
  cohort?: "variant_a" | "variant_b" | "both";
};

type SimResult = {
  scenario_segment: string;
  cohort: "variant_a" | "variant_b";
  resonance: Record<string, number>;
  confidence: string;
  rationale: string;
  friction_points: string[];
  what_worked: string[];
  metacognitive_reflection?: string;
};

type Props = {
  topFriction: FrictionTheme[];
  whatWorkedThemes: FrictionTheme[];
  trustSignalGaps: string[];
  foggAvg: Record<string, Record<string, number>>;
  winner: string;
  simulationResults: SimResult[];
  isSingleScreen?: boolean;
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
  if (isWorked) {
    if (motivation > 7) return "Motiv ↑";
    if (ability > 7) return "Ability ↑";
    return null;
  }
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
      return reflection.length > 120 ? reflection.slice(0, 119) + "…" : reflection;
    }
  }
  return null;
}

function Tip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <span className="relative group/tip inline-block">
      {children}
      <span className="pointer-events-none absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 rounded bg-neutral-800 text-white text-[10px] leading-snug px-2 py-1.5 opacity-0 group-hover/tip:opacity-100 transition-opacity whitespace-normal shadow-lg">
        {text}
        <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-800" />
      </span>
    </span>
  );
}

const FOGG_TOOLTIP: Record<string, string> = {
  "Ability ↓": "Ability: how easy the page makes it to take action. A low score means this persona hit friction — unclear steps, missing info, or cognitive overload.",
  "Ability ↑": "Ability: low friction detected. The page made it easy for this segment to act.",
  "Motiv ↓": "Motivation: how strongly this persona wants to act. A low score means weak emotional fit or poor relevance to their situation.",
  "Motiv ↑": "Motivation: strong desire to act observed. The page resonated emotionally with this segment.",
};

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

// Render a tiny "A" / "B" chip identifying which variant a theme came from.
// Hidden in single-screen mode and when the synthesizer couldn't attribute it.
function CohortChip({ cohort }: { cohort?: "variant_a" | "variant_b" | "both" }) {
  if (!cohort || cohort === "both") return null;
  const label = cohort === "variant_a" ? "A" : "B";
  const cls =
    cohort === "variant_a"
      ? "bg-sky-50 border-sky-200 text-sky-700"
      : "bg-violet-50 border-violet-200 text-violet-700";
  return (
    <span
      className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold ${cls}`}
      title={`From variant ${label}`}
    >
      {label}
    </span>
  );
}

export default function BlockersMatrix({
  topFriction,
  whatWorkedThemes,
  trustSignalGaps,
  foggAvg,
  winner,
  simulationResults,
  isSingleScreen,
}: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const sortedFriction = [...topFriction].sort(
    (a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3) ||
      b.count - a.count
  );

  const sortedWorked = [...whatWorkedThemes].sort((a, b) => b.count - a.count);
  const rows = [
    ...sortedFriction.map((t) => ({ theme: t, isWorked: false })),
    ...sortedWorked.map((t) => ({ theme: t, isWorked: true })),
  ];

  if (!rows.length && !trustSignalGaps.length) return null;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-semibold text-sm">🚦 Conversion Blockers & Wins</h2>
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
                    {!isSingleScreen && <CohortChip cohort={t.cohort} />}
                    <span className="text-[10px] text-neutral-500">
                      {t.count} agent{t.count !== 1 ? "s" : ""}
                    </span>
                    {foggBadge && (
                      <Tip text={FOGG_TOOLTIP[foggBadge] ?? foggBadge}>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded border font-medium cursor-help ${
                            foggBadge.includes("↑")
                              ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                              : "bg-red-50 border-red-200 text-red-700"
                          }`}
                        >
                          {foggBadge}
                        </span>
                      </Tip>
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
                <div className="mt-2 space-y-1.5">
                  {t.example_quotes.map((q, j) => (
                    <div key={j} className="text-xs text-neutral-600">
                      <span className="italic">&ldquo;{q.quote}&rdquo;</span>
                      {(q.agent_idx != null || q.segment) && (
                        <span className="ml-2 text-[10px] text-neutral-400 not-italic">
                          —{q.agent_idx != null ? ` Agent #${q.agent_idx}` : ""}
                          {q.segment ? ` (${q.segment})` : ""}
                        </span>
                      )}
                    </div>
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
