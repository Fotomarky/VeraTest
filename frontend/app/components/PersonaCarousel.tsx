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
  personas: ScenarioCard[];
  resultsBySegment: Map<string, SimResult[]>;
  winner: string;
  isSingleScreen?: boolean;
};

type VerdictTint = "winner" | "loser" | "split";

function getVerdictTint(results: SimResult[], winner: string): VerdictTint {
  if (!results.length) return "split";
  const aScores = results.filter((r) => r.cohort === "variant_a").map((r) => r.resonance_overall);
  const bScores = results.filter((r) => r.cohort === "variant_b").map((r) => r.resonance_overall);
  if (!aScores.length || !bScores.length) return "split";
  const avgA = aScores.reduce((s, v) => s + v, 0) / aScores.length;
  const avgB = bScores.reduce((s, v) => s + v, 0) / bScores.length;
  if (Math.abs(avgA - avgB) <= 1.0) return "split";
  const preferred = avgA > avgB ? "variant_a" : "variant_b";
  return preferred === winner ? "winner" : "loser";
}

const SEGMENT_COLORS = ["#F5C518", "#4FC3F7", "#81C784", "#FF8A65", "#CE93D8"];

const TINT_STRIP: Record<VerdictTint, string> = {
  winner: "bg-emerald-400",
  loser: "bg-red-400",
  split: "bg-amber-400",
};

const TINT_RING: Record<VerdictTint, string> = {
  winner: "ring-emerald-200",
  loser: "ring-red-200",
  split: "ring-amber-200",
};

export default function PersonaCarousel({ personas, resultsBySegment, winner, isSingleScreen }: Props) {
  const sorted = [...personas].sort((a, b) => {
    const aCount = resultsBySegment.get(a.segment)?.length ?? 0;
    const bCount = resultsBySegment.get(b.segment)?.length ?? 0;
    return bCount - aCount;
  });

  const [index, setIndex] = useState(0);

  if (!sorted.length) return null;

  const current = sorted[index];
  const results = resultsBySegment.get(current.segment) ?? [];
  const tint = getVerdictTint(results, winner);
  const originalIndex = personas.indexOf(current);
  const segmentColor = originalIndex >= 0 ? SEGMENT_COLORS[originalIndex % SEGMENT_COLORS.length] : undefined;

  return (
    <section>
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <h2 className="font-semibold text-sm">
          Persona Diagnostics
          <span className="text-neutral-400 font-normal ml-2">
            ({sorted.length} segment{sorted.length !== 1 ? "s" : ""})
          </span>
        </h2>
        <span className="text-xs text-neutral-500">
          Persona {index + 1} of {sorted.length} · {results.length} agent
          {results.length !== 1 ? "s" : ""} · {current.segment}
        </span>
      </div>

      <div className="relative px-5">
        {/* Prev arrow */}
        {sorted.length > 1 && (
          <button
            onClick={() => setIndex((i) => (i - 1 + sorted.length) % sorted.length)}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-white border border-neutral-200 shadow-sm hover:bg-neutral-50 text-neutral-500"
            aria-label="Previous persona"
          >
            ‹
          </button>
        )}

        {/* Card with verdict tint strip */}
        <div className={`rounded-lg overflow-hidden ring-1 ${TINT_RING[tint]}`}>
          <div className={`h-1 ${TINT_STRIP[tint]}`} />
          <PersonaCard persona={current} results={results} winner={winner} segmentColor={segmentColor} isSingleScreen={isSingleScreen} />
        </div>

        {/* Next arrow */}
        {sorted.length > 1 && (
          <button
            onClick={() => setIndex((i) => (i + 1) % sorted.length)}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-white border border-neutral-200 shadow-sm hover:bg-neutral-50 text-neutral-500"
            aria-label="Next persona"
          >
            ›
          </button>
        )}
      </div>

      {/* Dot indicators */}
      {sorted.length > 1 && (
        <div className="flex justify-center gap-1.5 mt-3">
          {sorted.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === index ? "w-3 bg-neutral-700" : "w-1.5 bg-neutral-300"
              }`}
              aria-label={`Go to persona ${i + 1}`}
            />
          ))}
        </div>
      )}
    </section>
  );
}
