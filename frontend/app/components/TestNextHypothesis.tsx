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
