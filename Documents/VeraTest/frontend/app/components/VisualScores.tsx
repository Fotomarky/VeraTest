type Props = {
  visualImpact: Record<string, number>;
  winner: string;
};

export default function VisualScores({ visualImpact, winner }: Props) {
  const scoreA = visualImpact["variant_a"] ?? 0;
  const scoreB = visualImpact["variant_b"] ?? 0;
  if (!scoreA && !scoreB) return null;

  const visualWinner = scoreA > scoreB ? "variant_a" : scoreB > scoreA ? "variant_b" : null;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="font-semibold text-sm">Visual impact per variant</h2>
        <span className="text-xs text-neutral-400">averaged across all agents · scored 1–10 per persona</span>
      </div>
      <div className="space-y-3">
        {(["variant_a", "variant_b"] as const).map((v) => {
          const score = v === "variant_a" ? scoreA : scoreB;
          const label = v === "variant_a" ? "Variant A" : "Variant B";
          const isVisualWinner = visualWinner === v;
          return (
            <div key={v}>
              <div className="flex items-center justify-between text-xs mb-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{label}</span>
                  {isVisualWinner && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">visually stronger</span>
                  )}
                  {!isVisualWinner && visualWinner !== null && winner === v && (
                    <span className="text-[10px] text-neutral-400">(converts better despite lower visual score)</span>
                  )}
                </div>
                <span className="font-semibold text-neutral-800">{score}/10</span>
              </div>
              <div className="h-2.5 bg-neutral-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${isVisualWinner ? "bg-amber-400" : "bg-neutral-300"}`}
                  style={{ width: `${(score / 10) * 100}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      {visualWinner && winner !== "neither" && visualWinner !== winner && (
        <p className="mt-3 text-xs text-neutral-500 bg-neutral-50 rounded p-2">
          ⚠ The visually stronger variant ({visualWinner === "variant_a" ? "A" : "B"}) was not the
          overall winner. Agents may have been influenced by messaging clarity, trust signals,
          or Fogg ability more than first-impression aesthetics.
        </p>
      )}
    </section>
  );
}