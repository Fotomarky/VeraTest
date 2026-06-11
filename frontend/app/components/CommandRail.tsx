"use client";

type SynthesisForRail = {
  directional_winner: "variant_a" | "variant_b" | "tie";
  cohort_resonance_overall: Record<string, number>;
  coverage_score: number;
  confound_warning?: string;
};

type FidelityForRail = {
  persona_consistency: number;
  agents_drifted: number;
  rationale_coherence?: number;
  agents_incoherent?: number;
};

type Props = {
  synthesis: SynthesisForRail | null;
  fidelity?: FidelityForRail | null;
  totalAgents?: number;
  runId: string;
  status: string;
  onCopyMarkdown: () => void;
  copied: boolean;
  elapsedSec?: number | null;
};

type Tier = "good" | "average" | "poor";

function tierFor(score: number): Tier {
  if (score >= 7) return "good";
  if (score >= 4) return "average";
  return "poor";
}

const TIER_TEXT: Record<Tier, string> = {
  good: "text-emerald-600",
  average: "text-amber-600",
  poor: "text-red-600",
};

const TIER_BG: Record<Tier, string> = {
  good: "bg-gradient-to-r from-emerald-100 via-emerald-50/40 to-white",
  average: "bg-gradient-to-r from-amber-100 via-amber-50/40 to-white",
  poor: "bg-gradient-to-r from-red-100 via-red-50/40 to-white",
};

const TIER_BORDER: Record<Tier, string> = {
  good: "border-emerald-200",
  average: "border-amber-200",
  poor: "border-red-200",
};

function fmtElapsed(sec: number | null | undefined): string {
  if (sec == null || !isFinite(sec) || sec <= 0) return "—";
  if (sec < 90) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s ? `${m}m ${s}s` : `${m}m`;
}

export default function CommandRail({
  synthesis,
  fidelity,
  totalAgents = 0,
  runId,
  status,
  onCopyMarkdown,
  copied,
  elapsedSec,
}: Props) {
  const isComplete = status === "complete";
  const inProgress = !isComplete && status !== "failed";

  if (inProgress) return null;

  const winner = synthesis?.directional_winner ?? "tie";
  const scoreA = synthesis?.cohort_resonance_overall?.["variant_a"] ?? 0;
  const scoreB = synthesis?.cohort_resonance_overall?.["variant_b"] ?? 0;
  const isSingleScreen = isComplete && scoreA > 0 && scoreB === 0;

  // Audience fit = average of cohorts present (single-screen → just A).
  const audienceFit = isSingleScreen
    ? scoreA
    : scoreA && scoreB
    ? (scoreA + scoreB) / 2
    : scoreA || scoreB;

  const tier = tierFor(audienceFit);
  const confoundWarning = synthesis?.confound_warning;

  const fidelityPct =
    fidelity != null ? Math.round(fidelity.persona_consistency * 100) : null;
  const stayedInPersona =
    fidelity != null ? Math.max(0, totalAgents - fidelity.agents_drifted) : null;
  const fidelityTitle =
    fidelity != null
      ? `LLM-as-a-Judge checked whether each of the ${totalAgents} agents stayed in its persona. ` +
        `${fidelity.agents_drifted} drifted out of character` +
        (fidelity.agents_incoherent != null
          ? `; ${fidelity.agents_incoherent} had a score/rationale mismatch.`
          : ".")
      : "";

  if (status === "failed") {
    return (
      <div className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-red-200 px-4 py-2">
        <span className="text-xs text-red-600 font-medium">Run failed</span>
      </div>
    );
  }

  return (
    <div
      className={`sticky top-0 z-50 backdrop-blur border-b ${TIER_BORDER[tier]} ${TIER_BG[tier]}`}
    >
      <div className="flex items-center gap-5 max-w-4xl mx-auto px-4 py-2.5 flex-wrap">
        {/* LEFT — Audience Fit score */}
        <div className="flex-shrink-0 flex flex-col gap-0 min-w-[120px]">
          <div
            className="text-[10px] uppercase tracking-wide text-neutral-500 font-semibold cursor-help"
            title="Scores how much the page resonates with the audience"
          >
            Audience Fit
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className={`text-2xl font-bold leading-none ${TIER_TEXT[tier]}`}>
              {audienceFit.toFixed(1)}
            </span>
            <span className="text-xs text-neutral-400">/10</span>
            {confoundWarning && (
              <span
                className="text-amber-600 cursor-help text-sm leading-none"
                title={`Test design issue: ${confoundWarning}`}
              >
                ⚠
              </span>
            )}
          </div>
        </div>

        {/* CENTER — winner statement (A/B only) or filler */}
        <div className="flex-1 min-w-0 text-center">
          {isComplete && !isSingleScreen ? (
            <div className="flex items-center justify-center gap-3">
              <span
                className={`text-sm font-semibold ${
                  winner === "tie"
                    ? "text-neutral-600"
                    : winner === "variant_a"
                    ? "text-neutral-800"
                    : "text-neutral-800"
                }`}
              >
                {winner === "tie"
                  ? "No clear winner"
                  : winner === "variant_a"
                  ? "Variant A wins"
                  : "Variant B wins"}
              </span>
              <span className="text-xs text-neutral-500 font-mono">
                <span className={winner === "variant_a" ? "text-neutral-900 font-semibold" : ""}>
                  A {scoreA.toFixed(1)}
                </span>
                <span className="text-neutral-300 mx-1.5">vs</span>
                <span className={winner === "variant_b" ? "text-neutral-900 font-semibold" : ""}>
                  B {scoreB.toFixed(1)}
                </span>
              </span>
            </div>
          ) : null}
        </div>

        {/* RIGHT — fidelity, duration, coverage, actions */}
        <div className="flex items-center gap-3 flex-shrink-0 text-[11px] text-neutral-500">
          {isComplete && fidelity != null && fidelityPct != null ? (
            <span title={fidelityTitle} className="cursor-help">
              <span className="text-emerald-600 font-medium">
                {stayedInPersona}/{totalAgents}
              </span>{" "}
              in persona
            </span>
          ) : isComplete ? (
            <span className="text-neutral-400">measuring…</span>
          ) : null}

          {elapsedSec != null && (
            <span className="text-neutral-500">{fmtElapsed(elapsedSec)}</span>
          )}

          {synthesis?.coverage_score != null && (
            <span className="text-neutral-400">
              coverage {synthesis.coverage_score}/100
            </span>
          )}

          <button
            onClick={onCopyMarkdown}
            className="px-2.5 py-1 text-[11px] rounded border border-neutral-300 bg-white/80 hover:bg-white"
          >
            {copied ? "✓ Copied" : "Copy MD"}
          </button>
          <a
            href={`/share/${runId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2.5 py-1 text-[11px] rounded bg-neutral-900 text-white hover:bg-neutral-700"
          >
            Share
          </a>
        </div>
      </div>
    </div>
  );
}
