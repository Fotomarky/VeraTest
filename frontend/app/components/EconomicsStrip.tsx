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
    <div className="rounded-lg border border-neutral-200 bg-gradient-to-r from-emerald-50 to-white overflow-hidden">
      <div className="grid grid-cols-2 divide-x divide-neutral-200">
        <div className="px-5 py-3">
          <div className="text-[10px] uppercase tracking-wide text-emerald-700 font-semibold">
            This pretest
          </div>
          <div className="mt-1 text-lg font-semibold text-neutral-900">
            {fmtElapsed(elapsedSec ?? null)} · ~$0.01
          </div>
          <div className="text-[11px] text-neutral-500">
            ~24 Gemini calls on the free tier — no traffic, no code
          </div>
        </div>
        <div className="px-5 py-3">
          <div className="text-[10px] uppercase tracking-wide text-neutral-400 font-semibold">
            A live A/B test
          </div>
          <div className="mt-1 text-lg font-semibold text-neutral-400 line-through decoration-neutral-300">
            4–6 weeks · $10k–$50k
          </div>
          <div className="text-[11px] text-neutral-400">
            traffic spend + engineering + analyst time, after you&apos;ve shipped both variants
          </div>
        </div>
      </div>
    </div>
  );
}
