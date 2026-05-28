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
  segmentColor?: string;
  isSingleScreen?: boolean;
};

const DEVICE_ICON: Record<string, string> = { desktop: "🖥", mobile: "📱", tablet: "📲" };
const STYLE_ICON: Record<string, string> = { analytical: "📊", impulse: "⚡", cautious: "🔍", social: "💬" };
const PATIENCE_COLOR: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-red-50 text-red-700 border-red-200",
};

const RESONANCE_META: Record<string, { label: string; color: string; tooltip: string }> = {
  motivation: {
    label: "Motivation",
    color: "bg-blue-400",
    tooltip: "How strongly this persona wants to take action. Driven by desire, emotion, and relevance to their goals.",
  },
  ability: {
    label: "Ability",
    color: "bg-violet-400",
    tooltip: "How easy the page makes it to act. Low scores indicate friction: unclear steps, missing info, or cognitive overload.",
  },
  identity: {
    label: "Identity",
    color: "bg-amber-400",
    tooltip: "How well the page matches this persona's self-image and values. High score = strong personal fit.",
  },
  situation: {
    label: "Situation",
    color: "bg-teal-400",
    tooltip: "How their current context (time pressure, device, mindset) shapes their response to the page.",
  },
  beliefs: {
    label: "Beliefs",
    color: "bg-pink-400",
    tooltip: "How well the page aligns with their existing worldview and prior expectations about the product or category.",
  },
  trigger: {
    label: "Trigger",
    color: "bg-orange-400",
    tooltip: "How effectively the page prompts them to act now — urgency cues, CTAs, and timing signals.",
  },
};

const DIM_ORDER = ["motivation", "ability", "identity", "situation", "beliefs", "trigger"];

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

function avgResonanceDims(results: SimResult[]): Record<string, number> {
  const sums: Record<string, number> = {};
  const counts: Record<string, number> = {};
  for (const r of results) {
    for (const [dim, score] of Object.entries(r.resonance ?? {})) {
      sums[dim] = (sums[dim] ?? 0) + score;
      counts[dim] = (counts[dim] ?? 0) + 1;
    }
  }
  const out: Record<string, number> = {};
  for (const dim of Object.keys(sums)) {
    out[dim] = Math.round((sums[dim] / counts[dim]) * 10) / 10;
  }
  return out;
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

function Tip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <span className="relative group/tip inline-block">
      {children}
      <span className="pointer-events-none absolute z-50 bottom-full left-0 mb-2 w-56 rounded bg-neutral-800 text-white text-[10px] leading-snug px-2 py-1.5 opacity-0 group-hover/tip:opacity-100 transition-opacity whitespace-normal shadow-lg">
        {text}
        <span className="absolute top-full left-0 ml-2 border-4 border-transparent border-t-neutral-800" />
      </span>
    </span>
  );
}

function AgentDot({ color }: { color: string }) {
  return (
    <svg width="12" height="16" viewBox="0 0 12 16" aria-hidden="true"
         style={{ display: "inline-block", flexShrink: 0 }}>
      {/* Hat */}
      <rect x="3" y="0" width="6" height="2" fill="#5C3A1E" />
      <rect x="2" y="2" width="8" height="1" fill="#5C3A1E" />
      {/* Head */}
      <rect x="4" y="3" width="4" height="3" fill="#F5CBA7" />
      {/* Body — segment color */}
      <rect x="3" y="6" width="6" height="4" fill={color} />
      {/* Legs */}
      <rect x="3" y="10" width="2" height="4" fill="#2C3E50" />
      <rect x="7" y="10" width="2" height="4" fill="#2C3E50" />
    </svg>
  );
}

export default function PersonaCard({ persona, results, winner, segmentColor, isSingleScreen }: Props) {
  const { pctA, pctB } = resonancePercents(results);
  const winningVariant = pctA > pctB ? "variant_a" : pctB > pctA ? "variant_b" : null;
  const dims = avgResonanceDims(results);
  const trustGaps = commonTrustGaps(results);
  const hasDims = Object.keys(dims).length > 0;

  return (
    <div
      className="rounded-lg border border-neutral-200 bg-white overflow-hidden"
      style={segmentColor ? { borderLeftWidth: "4px", borderLeftColor: segmentColor } : undefined}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-100 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            {segmentColor && <AgentDot color={segmentColor} />}
            <div className="font-semibold text-sm truncate">{persona.segment}</div>
          </div>
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

      {/* Vote bar — hidden in single-screen mode */}
      {!isSingleScreen && (
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
      )}

      {/* Resonance dimensions — all 6 */}
      {hasDims && (
        <div className="px-4 py-2 border-t border-neutral-100 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          {DIM_ORDER.filter((d) => dims[d] != null).map((dim) => {
            const meta = RESONANCE_META[dim];
            const score = dims[dim];
            return (
              <div key={dim}>
                <Tip text={meta?.tooltip ?? dim}>
                  <div className="text-neutral-400 mb-0.5 cursor-help underline decoration-dotted decoration-neutral-300 inline-block">
                    {meta?.label ?? dim}
                  </div>
                </Tip>
                <div className="flex items-center gap-1.5">
                  <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${meta?.color ?? "bg-neutral-400"}`}
                      style={{ width: `${(score / 10) * 100}%` }}
                    />
                  </div>
                  <span className="font-medium text-neutral-700 w-6 text-right">{score}</span>
                </div>
              </div>
            );
          })}
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
