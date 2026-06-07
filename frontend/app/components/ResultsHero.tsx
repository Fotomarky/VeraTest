"use client";
import { useState } from "react";
import PersonaCard from "./PersonaCard";

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
  runId: string;
  personas: ScenarioCard[];
  resultsBySegment: Map<string, SimResult[]>;
  winner: "variant_a" | "variant_b" | "tie";
  isSingleScreen: boolean;
};

const STYLE_ICON: Record<string, string> = { analytical: "📊", impulse: "⚡", cautious: "🔍", social: "💬" };
const DEVICE_ICON: Record<string, string> = { desktop: "🖥", mobile: "📱", tablet: "📲" };

function cleanPersona(name: string): string {
  return name.replace(/^\s*(?:the|a|an)\s+/i, "").trim() || name;
}

function leanPercents(results: SimResult[]): { pctA: number; pctB: number } {
  const a = results.filter((r) => r.cohort === "variant_a").map((r) => r.resonance_overall);
  const b = results.filter((r) => r.cohort === "variant_b").map((r) => r.resonance_overall);
  const avgA = a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0;
  const avgB = b.length ? b.reduce((s, v) => s + v, 0) / b.length : 0;
  const total = avgA + avgB;
  if (total === 0) return { pctA: 50, pctB: 50 };
  const pctA = Math.round((avgA / total) * 100);
  return { pctA, pctB: 100 - pctA };
}

function avgOverall(results: SimResult[]): number {
  if (!results.length) return 0;
  return results.reduce((s, r) => s + r.resonance_overall, 0) / results.length;
}

function topFrictionPoint(results: SimResult[]): string | null {
  for (const r of results) {
    if (r.friction_points && r.friction_points.length) return r.friction_points[0];
  }
  return null;
}

export default function ResultsHero({ runId, personas, resultsBySegment, winner, isSingleScreen }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const sorted = [...personas].sort((a, b) => {
    const ac = resultsBySegment.get(a.segment)?.length ?? 0;
    const bc = resultsBySegment.get(b.segment)?.length ?? 0;
    return bc - ac;
  });

  const totalAgents = Array.from(resultsBySegment.values()).reduce((s, r) => s + r.length, 0);
  const selectedPersona = sorted.find((p) => p.segment === selected) ?? null;
  const selectedResults = selectedPersona ? resultsBySegment.get(selectedPersona.segment) ?? [] : [];

  return (
    <section>
      <div className="rounded-lg border border-neutral-200 bg-white p-5">
        <div className="grid grid-cols-[auto_1fr] gap-6 items-center max-sm:grid-cols-1">
          {/* Variant thumbnails */}
          <div className="flex gap-2">
            <Thumb runId={runId} which="a" label="A" win={winner === "variant_a"} />
            {!isSingleScreen && (
              <Thumb runId={runId} which="b" label="B" win={winner === "variant_b"} />
            )}
          </div>

          {/* Persona circles */}
          <div>
            <div className="text-[11px] uppercase tracking-wide text-neutral-400 mb-3">
              Who tested it · {totalAgents} agents across {sorted.length} persona{sorted.length !== 1 ? "s" : ""}
            </div>
            <div className="flex gap-5 flex-wrap">
              {sorted.map((p) => {
                const results = resultsBySegment.get(p.segment) ?? [];
                const count = results.length;
                let ring: string;
                let leanLabel: string;
                if (isSingleScreen) {
                  const pos = Math.max(0, Math.min(100, Math.round((avgOverall(results) / 10) * 100)));
                  ring = `conic-gradient(#22c55e 0 ${pos}%, #ef4444 ${pos}% 100%)`;
                  leanLabel = pos >= 60 ? "positive" : pos >= 40 ? "mixed" : "negative";
                } else {
                  const { pctA, pctB } = leanPercents(results);
                  ring = `conic-gradient(#3b82f6 0 ${pctA}%, #8b5cf6 ${pctA}% 100%)`;
                  leanLabel = Math.abs(pctA - pctB) <= 4 ? "split" : pctA > pctB ? "leans A" : "leans B";
                }
                const isActive = selected === p.segment;
                const tip = topFrictionPoint(results);
                return (
                  <button
                    key={p.segment}
                    onClick={() => setSelected(isActive ? null : p.segment)}
                    aria-expanded={isActive}
                    aria-label={`${cleanPersona(p.segment)}, ${count} agent${count !== 1 ? "s" : ""}, ${leanLabel}${tip ? `, top friction: ${tip}` : ""}`}
                    className="group relative flex flex-col items-center gap-1 w-24 text-center"
                  >
                    <div
                      className={`w-16 h-16 rounded-full p-1 transition-transform group-hover:scale-105 ${
                        isActive ? "ring-2 ring-blue-500" : ""
                      }`}
                      style={{ background: ring }}
                    >
                      <div className="w-full h-full rounded-full bg-white flex items-center justify-center text-xl">
                        {STYLE_ICON[p.decision_style] ?? DEVICE_ICON[p.device] ?? "🧑"}
                      </div>
                    </div>
                    <div className="text-[11px] font-semibold leading-tight line-clamp-2">
                      {cleanPersona(p.segment)}
                    </div>
                    <div className="text-[10px] text-neutral-400">
                      {count} agent{count !== 1 ? "s" : ""} · {leanLabel}
                      {isActive ? " ▾" : ""}
                    </div>

                    {/* hover tooltip preview */}
                    <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 rounded bg-neutral-800 text-white text-[10px] leading-snug px-2 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity shadow-lg z-20 text-left">
                      <span className="font-semibold block">{cleanPersona(p.segment)}</span>
                      <span className="text-neutral-300">
                        {count} agents · {leanLabel}
                      </span>
                      {tip && <span className="block text-neutral-300 mt-0.5">Top friction: {tip}</span>}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* legend */}
            <div className="flex gap-4 flex-wrap text-[10px] text-neutral-400 mt-3">
              {isSingleScreen ? (
                <>
                  <Legend color="#22c55e" label="positive" />
                  <Legend color="#ef4444" label="negative" />
                </>
              ) : (
                <>
                  <Legend color="#3b82f6" label="leans A" />
                  <Legend color="#8b5cf6" label="leans B" />
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* expanded persona detail */}
      {selectedPersona && (
        <div className="mt-3">
          <PersonaCard
            persona={selectedPersona}
            results={selectedResults}
            winner={winner}
            isSingleScreen={isSingleScreen}
          />
        </div>
      )}
    </section>
  );
}

function Thumb({
  runId,
  which,
  label,
  win,
}: {
  runId: string;
  which: "a" | "b";
  label: string;
  win: boolean;
}) {
  return (
    <div className="relative w-[84px] h-[120px] rounded-lg border border-neutral-200 overflow-hidden bg-neutral-100">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/runs/${runId}/image/${which}`}
        alt={`Variant ${label}`}
        className="w-full h-full object-cover"
      />
      <span className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-[10px] font-bold text-center py-0.5">
        {label}
        {win ? " ★" : ""}
      </span>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}
