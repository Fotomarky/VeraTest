"use client";

function fmtElapsed(sec: number | null): string {
  if (sec == null || !isFinite(sec) || sec <= 0) return "~90s";
  if (sec < 90) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s ? `${m}m ${s}s` : `${m}m`;
}

export default function EconomicsStrip({ elapsedSec }: { elapsedSec?: number | null }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-gradient-to-r from-emerald-50 to-white px-5 py-3">
      <div className="text-[10px] uppercase tracking-wide text-emerald-700 font-semibold">
        This pretest
      </div>
      <div className="mt-1 text-lg font-semibold text-neutral-900">
        Completed in {fmtElapsed(elapsedSec ?? null)}
      </div>
      <div className="text-[11px] text-neutral-500">
        no traffic, no code — synthetic audience only
      </div>
    </div>
  );
}
