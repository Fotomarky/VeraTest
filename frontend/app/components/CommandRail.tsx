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
          {isComplete && (
            <>
              {synthesis?.coverage_score != null && (
                <span className="text-[10px] text-neutral-400">
                  coverage {synthesis.coverage_score}/100
                </span>
              )}
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
