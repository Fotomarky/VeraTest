"use client";
import { useState } from "react";

type Props = {
  runId: string;
  winner: string;
  visualImpact: Record<string, number>;
  confoundWarning?: string;
  isSingleScreen?: boolean;
};

export default function VisualEvidence({
  runId,
  winner,
  visualImpact,
  confoundWarning,
  isSingleScreen,
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
          <div className={`grid grid-cols-1 gap-4 ${isSingleScreen ? "max-w-md" : "sm:grid-cols-2"}`}>
            {(isSingleScreen ? (["a"] as const) : (["a", "b"] as const)).map((which) => {
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
