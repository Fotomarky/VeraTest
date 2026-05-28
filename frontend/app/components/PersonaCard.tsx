"use client";

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
  persona: ScenarioCard;
  results: SimResult[];
  winner: string;
};

const DEVICE_ICON: Record<string, string> = { desktop: "🖥", mobile: "📱", tablet: "📲" };
const STYLE_ICON: Record<string, string> = { analytical: "📊", impulse: "⚡", cautious: "🔍", social: "💬" };
const PATIENCE_COLOR: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-red-50 text-red-700 border-red-200",
};

function resonancePercents(results: SimResult[]): { pctA: number; pctB: number } {
  const aScores = results.filter((r) => r.cohort === "variant_a").map((r) => r.resonance_overall);
  const bScores = results.filter((r) => r.cohort === "variant_b").map((r) => r.resonance_overall);
  const avgA = aScores.length ? aScores.reduce((s, v) => s + v, 0) / aScores.length : 0;
  const avgB = bScores.length ? bScores.reduce((s, v) => s + v, 0) / bScores.length : 0;
  const total = avgA + avgB;
  if (total === 0) return { pctA: 50, pctB: 50 };
  const pctA = Math.round((avgA / total) * 100);
  return { pctA, pctB: 100 - pctA };
}

function avgFogg(results: SimResult[]): { motivation: number; ability: number } | null {
  const ms = results.map((r) => r.resonance?.["motivation"] ?? 0).filter((v) => v > 0);
  const as_ = results.map((r) => r.resonance?.["ability"] ?? 0).filter((v) => v > 0);
  if (!ms.length && !as_.length) return null;
  const avg = (arr: number[]) =>
    arr.length ? Math.round((arr.reduce((a, b) => a + b, 0) / arr.length) * 10) / 10 : 0;
  return { motivation: avg(ms), ability: avg(as_) };
}

function commonTrustGaps(results: SimResult[]): string[] {
  const counter: Record<string, number> = {};
  for (const r of results) {
    for (const gap of r.trust_signals_missing || []) {
      counter[gap] = (counter[gap] || 0) + 1;
    }
  }
  return Object.entries(counter)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([k]) => k);
}

export default function PersonaCard({ persona, results, winner }: Props) {
  const { pctA, pctB } = resonancePercents(results);
  const winningVariant = pctA > pctB ? "variant_a" : pctB > pctA ? "variant_b" : null;
  const fogg = avgFogg(results);
  const trustGaps = commonTrustGaps(results);

  return (
    <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-100 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-semibold text-sm truncate">{persona.segment}</div>
          <p className="text-xs text-neutral-500 mt-0.5 leading-snug line-clamp-2">
            {persona.context || "No context provided"}
          </p>
          {persona.communication_style && (
            <p className="text-xs text-neutral-400 mt-0.5 italic">{persona.communication_style}</p>
          )}
        </div>
        <div className="flex gap-1 shrink-0 flex-wrap justify-end">
          <Badge>{DEVICE_ICON[persona.device] || "💻"} {persona.device}</Badge>
          <Badge>{STYLE_ICON[persona.decision_style] || "🧠"} {persona.decision_style}</Badge>
          {persona.patience_threshold && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${PATIENCE_COLOR[persona.patience_threshold] || ""}`}>
              ⏱ {persona.patience_threshold} patience
            </span>
          )}
        </div>
      </div>

      {/* Vote bar */}
      <div className="px-4 pt-3 pb-1">
        <div className="flex items-center justify-between text-xs text-neutral-500 mb-1">
          <span>Variant A</span>
          <span className="font-medium text-neutral-800">{results.length} agent{results.length !== 1 ? "s" : ""}</span>
          <span>Variant B</span>
        </div>
        <div className="flex h-2 rounded-full overflow-hidden bg-neutral-100">
          <div
            className={`h-full transition-all ${winner === "variant_a" && winningVariant === "variant_a" ? "bg-emerald-500" : "bg-blue-400"}`}
            style={{ width: `${pctA}%` }}
          />
          <div
            className={`h-full transition-all ${winner === "variant_b" && winningVariant === "variant_b" ? "bg-emerald-500" : "bg-violet-400"}`}
            style={{ width: `${pctB}%` }}
          />
        </div>
        <div className="flex justify-between text-xs font-medium mt-1">
          <span className={winningVariant === "variant_a" ? "text-emerald-700" : "text-neutral-400"}>{pctA}%</span>
          <span className={winningVariant === "variant_b" ? "text-emerald-700" : "text-neutral-400"}>{pctB}%</span>
        </div>
      </div>

      {/* Fogg scores */}
      {fogg && (fogg.motivation > 0 || fogg.ability > 0) && (
        <div className="px-4 py-2 border-t border-neutral-100 grid grid-cols-2 gap-2 text-xs">
          <div>
            <div className="text-neutral-400 mb-0.5">Motivation</div>
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-400 rounded-full" style={{ width: `${(fogg.motivation / 10) * 100}%` }} />
              </div>
              <span className="font-medium text-neutral-700 w-6 text-right">{fogg.motivation}</span>
            </div>
          </div>
          <div>
            <div className="text-neutral-400 mb-0.5">Ability</div>
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                <div className="h-full bg-violet-400 rounded-full" style={{ width: `${(fogg.ability / 10) * 100}%` }} />
              </div>
              <span className="font-medium text-neutral-700 w-6 text-right">{fogg.ability}</span>
            </div>
          </div>
        </div>
      )}

      {/* Trust gaps */}
      {trustGaps.length > 0 && (
        <div className="px-4 py-2 border-t border-neutral-100">
          <div className="text-xs text-neutral-400 mb-1.5">Missing trust signals</div>
          <div className="flex flex-wrap gap-1">
            {trustGaps.map((gap, i) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 border border-red-200 text-red-700">
                {gap}
              </span>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-600 whitespace-nowrap">
      {children}
    </span>
  );
}

