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
