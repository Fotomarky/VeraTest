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

function votePercent(results: SimResult[], variant: string): number {
  if (!results.length) return 0;
  return Math.round((results.filter((r) => r.verdict === variant).length / results.length) * 100);
}

function avgVisualImpact(results: SimResult[]): Record<string, number> {
  const totals: Record<string, number> = {};
  const counts: Record<string, number> = {};
  for (const r of results) {
    for (const [v, score] of Object.entries(r.visual_impact || {})) {
      totals[v] = (totals[v] || 0) + score;
      counts[v] = (counts[v] || 0) + 1;
    }
  }
  return Object.fromEntries(
    Object.entries(totals).map(([v, t]) => [v, Math.round((t / counts[v]) * 10) / 10])
  );
}

function avgFogg(results: SimResult[]): { motivation: number; ability: number } | null {
  const ms = results.map((r) => r.fogg_motivation || 0).filter((v) => v > 0);
  const as_ = results.map((r) => r.fogg_ability || 0).filter((v) => v > 0);
  if (!ms.length && !as_.length) return null;
  const avg = (arr: number[]) =>
    arr.length ? Math.round((arr.reduce((a, b) => a + b, 0) / arr.length) * 10) / 10 : 0;
  return { motivation: avg(ms), ability: avg(as_) };
}

function topAttentionPath(results: SimResult[]): string[] {
  let best: string[] = [];
  for (const r of results) {
    if ((r.attention_path?.length || 0) > best.length) best = r.attention_path || [];
  }
  return best.slice(0, 5);
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
  const pctA = votePercent(results, "variant_a");
  const pctB = votePercent(results, "variant_b");
  const winningVariant = pctA > pctB ? "variant_a" : pctB > pctA ? "variant_b" : null;
  const avgImpact = avgVisualImpact(results);
  const fogg = avgFogg(results);
  const attentionPath = topAttentionPath(results);
  const trustGaps = commonTrustGaps(results);

  const alignments = results.map((r) => r.messaging_alignment).filter(Boolean);
  const topAlignment = alignments.length
    ? (["strong", "moderate", "weak"].find(
        (a) => alignments.filter((x) => x === a).length > alignments.length / 2
      ) ?? "moderate")
    : null;

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

      {/* Visual impact scores */}
      {(avgImpact["variant_a"] || avgImpact["variant_b"]) ? (
        <div className="px-4 py-2 border-t border-neutral-100 grid grid-cols-2 gap-2 text-xs">
          {(["variant_a", "variant_b"] as const).map((v) => (
            <div key={v}>
              <div className="text-neutral-400 mb-0.5">{v === "variant_a" ? "A" : "B"} visual</div>
              <div className="flex items-center gap-1.5">
                <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-400 rounded-full" style={{ width: `${((avgImpact[v] || 0) / 10) * 100}%` }} />
                </div>
                <span className="font-medium text-neutral-700 w-6 text-right">{avgImpact[v] ?? "—"}</span>
              </div>
            </div>
          ))}
        </div>
      ) : null}

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

      {/* Attention path */}
      {attentionPath.length > 0 && (
        <div className="px-4 py-2 border-t border-neutral-100">
          <div className="text-xs text-neutral-400 mb-1.5">Noticed in order</div>
          <div className="flex flex-wrap gap-1">
            {attentionPath.map((el, i) => (
              <span key={i} className="flex items-center gap-1 text-xs bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded-full">
                <span className="text-neutral-400 text-[10px]">{i + 1}</span>
                {el}
              </span>
            ))}
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

      {/* Messaging alignment */}
      {topAlignment && (
        <div className="px-4 py-2 border-t border-neutral-100 flex items-center gap-2">
          <span className="text-xs text-neutral-400">Messaging</span>
          <AlignmentBadge value={topAlignment} />
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

function AlignmentBadge({ value }: { value: string }) {
  const styles: Record<string, string> = {
    strong: "bg-emerald-50 text-emerald-700 border-emerald-200",
    moderate: "bg-amber-50 text-amber-700 border-amber-200",
    weak: "bg-red-50 text-red-700 border-red-200",
  };
  const labels: Record<string, string> = {
    strong: "✓ Strong match",
    moderate: "~ Moderate match",
    weak: "✗ Weak match",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-medium ${styles[value] || ""}`}>
      {labels[value] || value}
    </span>
  );
}