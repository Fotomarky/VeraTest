"use client";
import { useEffect, useState } from "react";
import PersonaCard from "../../components/PersonaCard";
import VisualScores from "../../components/VisualScores";
import FrictionList from "../../components/FrictionList";

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
  metacognitive_reflection?: string;
};

type Run = {
  run_id: string;
  status: string;
  goal: string;
  scenarios?: ScenarioCard[];
  simulation_results?: SimResult[];
  audit?: { trust_level: string; warnings: string[]; recommended_action: string };
  synthesis?: {
    winner: string;
    weighted_vote: Record<string, number>;
    coverage_score: number;
    top_friction: Array<{ theme: string; count: number; severity: "high" | "medium" | "low"; example_quotes: string[] }>;
    what_worked_themes: Array<{ theme: string; count: number; severity: "high" | "medium" | "low"; example_quotes: string[] }>;
    one_line_summary?: string;
    recommendation?: string;
    visual_impact?: Record<string, number>;
    confound_warning?: string;
    fogg_avg?: Record<string, Record<string, number>>;
    trust_signal_gaps?: string[];
  };
  error?: string;
};

const PHASE_LABELS: Record<string, string> = {
  pending: "Queued — waiting for the orchestrator",
  normalizing: "Reading the brief — analysing variants and extracting personas",
  building_scenarios: "Building scenarios — assigning agents proportionally to traffic",
  simulating: "Running simulation agents in parallel",
  auditing: "Auditing — checking for bias and confidence collapse",
  synthesizing: "Synthesising final report — clustering friction themes",
  complete: "Complete",
  failed: "Failed",
};

// Ordered phase sequence for the progress indicator. Excludes terminal states.
const PHASE_ORDER = [
  "pending",
  "normalizing",
  "building_scenarios",
  "simulating",
  "auditing",
  "synthesizing",
] as const;

const PHASE_SHORT: Record<string, string> = {
  pending: "Queued",
  normalizing: "Brief",
  building_scenarios: "Scenarios",
  simulating: "Simulate",
  auditing: "Audit",
  synthesizing: "Synthesise",
};

function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m > 0 ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

export default function RunPage({ params }: { params: { id: string } }) {
  const [run, setRun] = useState<Run | null>(null);
  const [copied, setCopied] = useState(false);
  const [mountedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    // Fire an immediate fetch so the page shows real data on first paint,
    // independent of how long it takes the SSE to deliver its first event.
    let cancelled = false;
    fetch(`/api/runs/${params.id}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data) setRun(data);
      })
      .catch(() => {});

    const source = new EventSource(`/api/runs/${params.id}/stream`);
    source.addEventListener("update", (e: MessageEvent) => {
      try {
        setRun(JSON.parse(e.data));
      } catch {}
    });
    source.onerror = () => {
      fetch(`/api/runs/${params.id}`).then((r) => r.json()).then(setRun).catch(() => {});
      source.close();
    };
    return () => {
      cancelled = true;
      source.close();
    };
  }, [params.id]);

  // Tick once a second while the run is in progress so the elapsed counter updates.
  useEffect(() => {
    if (!run) {
      const i = setInterval(() => setNow(Date.now()), 1000);
      return () => clearInterval(i);
    }
    if (run.status === "complete" || run.status === "failed") return;
    const i = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(i);
  }, [run]);

  async function copyMarkdown() {
    try {
      const r = await fetch(`/api/runs/${params.id}/export.md`);
      const text = await r.text();
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  if (!run) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div>
          <h1 className="text-2xl font-semibold">Connecting…</h1>
          <div className="text-xs font-mono text-neutral-400 mt-1">{params.id}</div>
        </div>
        <ProgressBlock
          status="pending"
          completed={0}
          total={20}
          elapsedMs={now - mountedAt}
        />
      </div>
    );
  }

  const completed = run.simulation_results?.length || 0;
  const total = run.scenarios?.length || 20;
  const inProgress = run.status !== "complete" && run.status !== "failed";
  const synth = run.synthesis;
  const winner = synth?.winner ?? "neither";

  const scenariosBySegment = new Map<string, ScenarioCard>();
  for (const sc of run.scenarios || []) {
    if (!scenariosBySegment.has(sc.segment)) scenariosBySegment.set(sc.segment, sc);
  }
  const uniquePersonas = Array.from(scenariosBySegment.values());

  const resultsBySegment = new Map<string, SimResult[]>();
  for (const r of run.simulation_results || []) {
    const bucket = resultsBySegment.get(r.scenario_segment) || [];
    bucket.push(r);
    resultsBySegment.set(r.scenario_segment, bucket);
  }

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Title + export actions */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold truncate">{run.goal}</h1>
          <div className="text-xs font-mono text-neutral-400 mt-1">{run.run_id}</div>
        </div>
        {run.status === "complete" && (
          <div className="flex gap-2 shrink-0">
            <button
              onClick={copyMarkdown}
              className="px-3 py-1.5 text-xs rounded-md border border-neutral-300 hover:bg-neutral-50"
            >
              {copied ? "✓ Copied" : "Copy as markdown"}
            </button>
            <a
              href={`/share/${run.run_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 text-xs rounded-md bg-neutral-900 text-white hover:bg-neutral-700"
            >
              Open share page
            </a>
          </div>
        )}
      </div>

      {/* Confound warning — highest priority */}
      {synth?.confound_warning && (
        <div className="rounded-lg border-2 border-orange-300 bg-orange-50 p-4">
          <div className="font-semibold text-sm text-orange-800 mb-1">⚠ Test design issue detected</div>
          <p className="text-sm text-orange-700">{synth.confound_warning}</p>
          <p className="text-xs text-orange-600 mt-2">
            Results below are shown for reference only — do not base decisions on a confounded test.
          </p>
        </div>
      )}

      {/* In-progress status */}
      {inProgress && (
        <ProgressBlock
          status={run.status}
          completed={completed}
          total={total}
          elapsedMs={now - mountedAt}
        />
      )}

      {/* Error */}
      {run.status === "failed" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="font-medium mb-1">Run failed</div>
          <div className="text-xs font-mono break-all">{run.error || "unknown error"}</div>
        </div>
      )}

      {/* Trust banner */}
      {run.audit && run.audit.trust_level !== "high" && (
        <div className={`rounded-lg border p-4 ${
          run.audit.trust_level === "medium" ? "border-amber-200 bg-amber-50" : "border-red-200 bg-red-50"
        }`}>
          <div className="font-medium text-sm mb-1">
            ⚠ Trust: {run.audit.trust_level.toUpperCase()} — {run.audit.recommended_action}
          </div>
          <ul className="text-xs text-neutral-700 space-y-0.5 list-disc list-inside">
            {run.audit.warnings?.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {/* Winner summary */}
      {synth && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5">
          <div className="flex items-baseline justify-between flex-wrap gap-2 mb-3">
            <h2 className="font-semibold">Result</h2>
            <div className="text-xs text-neutral-400">coverage {synth.coverage_score}/100</div>
          </div>
          {winner === "neither" ? (
            <div className="text-neutral-600 text-sm">Neither variant emerged as a clear winner.</div>
          ) : (
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="text-2xl font-bold font-mono uppercase">
                {winner === "variant_a" ? "Variant A" : "Variant B"}
              </span>
              <span className="text-sm text-neutral-500">
                {((synth.weighted_vote?.[winner] ?? 0) * 100).toFixed(0)}% weighted vote
              </span>
            </div>
          )}
          {synth.one_line_summary && (
            <p className="mt-2 text-sm text-neutral-600 italic">{synth.one_line_summary}</p>
          )}
          {synth.recommendation && (
            <p className="mt-2 text-sm text-neutral-700">{synth.recommendation}</p>
          )}
        </section>
      )}

      {/* Visual impact scores */}
      {synth?.visual_impact && Object.keys(synth.visual_impact).length > 0 && (
        <VisualScores visualImpact={synth.visual_impact} winner={winner} />
      )}

      {/* Variant images */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <VariantCard runId={run.run_id} which="a" winner={winner === "variant_a"} />
        <VariantCard runId={run.run_id} which="b" winner={winner === "variant_b"} />
      </div>

      {/* Persona cards */}
      {uniquePersonas.length > 0 && (
        <section>
          <h2 className="font-semibold text-sm mb-3">
            How your personas evaluated it
            <span className="text-neutral-400 font-normal ml-2">({uniquePersonas.length} segments)</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {uniquePersonas.map((p) => (
              <PersonaCard
                key={p.segment}
                persona={p}
                results={resultsBySegment.get(p.segment) || []}
                winner={winner}
              />
            ))}
          </div>
        </section>
      )}

      {/* Friction themes */}
      {synth?.top_friction && (
        <FrictionList themes={synth.top_friction} title="Top friction in losing variant" />
      )}

      {/* What worked */}
      {synth?.what_worked_themes && synth.what_worked_themes.length > 0 && (
        <FrictionList
          themes={synth.what_worked_themes}
          title="What worked in the winning variant"
          emptyMessage="No specific strengths detected."
        />
      )}

      {/* Fogg diagnostics */}
      {synth?.fogg_avg && Object.keys(synth.fogg_avg).length > 0 && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-semibold text-sm">Fogg B=MAP diagnostics</h2>
            <span className="text-xs text-neutral-400">averaged across agents per variant chosen</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Object.entries(synth.fogg_avg).map(([variant, scores]) => (
              <div key={variant} className="space-y-2">
                <div className="text-xs font-medium text-neutral-600 uppercase">{variant.replace("_", " ")}</div>
                {Object.entries(scores).map(([dim, val]) => (
                  <div key={dim}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="capitalize text-neutral-500">{dim}</span>
                      <span className="font-medium">{val}/10</span>
                    </div>
                    <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${dim === "motivation" ? "bg-blue-400" : "bg-violet-400"}`}
                        style={{ width: `${(val / 10) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
          {(() => {
            const a = synth.fogg_avg["variant_a"];
            const b = synth.fogg_avg["variant_b"];
            if (a && b) {
              const abilityGap = Math.abs((a.ability || 0) - (b.ability || 0));
              if (abilityGap > 2) {
                const easier = (b.ability || 0) > (a.ability || 0) ? "Variant B" : "Variant A";
                return (
                  <p className="mt-3 text-xs text-neutral-500 bg-neutral-50 rounded p-2">
                    💡 {easier} scores significantly higher on Ability — the path to conversion is
                    clearer. Consider applying its CTA structure to the other variant.
                  </p>
                );
              }
            }
            return null;
          })()}
        </section>
      )}

      {/* Trust signal gaps */}
      {synth?.trust_signal_gaps && synth.trust_signal_gaps.length > 0 && (
        <section className="rounded-lg border border-red-100 bg-red-50 p-5">
          <h2 className="font-semibold text-sm text-red-800 mb-2">
            Trust signals reported missing by agents
          </h2>
          <div className="flex flex-wrap gap-2">
            {synth.trust_signal_gaps.map((gap, i) => (
              <span key={i} className="text-xs px-2 py-1 rounded bg-white border border-red-200 text-red-700 font-medium">
                {gap}
              </span>
            ))}
          </div>
          <p className="text-xs text-red-600 mt-2">
            Adding these to the winning variant may increase conversion further.
          </p>
        </section>
      )}

      {/* Scenario voices */}
      {run.simulation_results && run.simulation_results.length > 0 && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5">
          <h2 className="font-semibold text-sm mb-2">All agent voices</h2>
          <details>
            <summary className="text-sm text-neutral-500 cursor-pointer select-none mb-3">
              View {run.simulation_results.length} individual responses
            </summary>
            <div className="space-y-3 mt-2">
              {run.simulation_results.map((r, i) => (
                <div key={i} className="border-l-2 border-neutral-200 pl-3 text-sm">
                  <div className="flex items-center gap-2 text-xs flex-wrap mb-1">
                    <span className="font-mono uppercase font-medium text-neutral-800">{r.verdict}</span>
                    <span className="text-neutral-400">·</span>
                    <span className="text-neutral-600">{r.scenario_segment}</span>
                    <span className="text-neutral-400">·</span>
                    <span className={
                      r.confidence === "high" ? "text-emerald-700"
                        : r.confidence === "medium" ? "text-amber-700"
                        : "text-red-700"
                    }>{r.confidence} confidence</span>
                    {r.messaging_alignment && (
                      <>
                        <span className="text-neutral-400">·</span>
                        <span className="text-neutral-500">msg: {r.messaging_alignment}</span>
                      </>
                    )}
                    {r.loss_gain_framing && r.loss_gain_framing !== "neutral" && (
                      <>
                        <span className="text-neutral-400">·</span>
                        <span className="text-neutral-500">{r.loss_gain_framing} framing</span>
                      </>
                    )}
                  </div>
                  {r.first_impression && (
                    <p className="text-xs text-neutral-500 italic mb-1">{r.first_impression}</p>
                  )}
                  <p className="text-neutral-700 italic break-words">"{r.rationale}"</p>
                  {r.metacognitive_reflection && (
                    <p className="text-xs text-neutral-400 mt-1">🔄 {r.metacognitive_reflection}</p>
                  )}
                  {r.attention_path && r.attention_path.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {r.attention_path.map((el, j) => (
                        <span key={j} className="text-[10px] bg-neutral-100 px-1.5 py-0.5 rounded text-neutral-500">
                          {j + 1}. {el}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </details>
        </section>
      )}
    </div>
  );
}

function ProgressBlock({
  status,
  completed,
  total,
  elapsedMs,
}: {
  status: string;
  completed: number;
  total: number;
  elapsedMs: number;
}) {
  const currentIdx = PHASE_ORDER.indexOf(status as (typeof PHASE_ORDER)[number]);
  const phaseLabel = PHASE_LABELS[status] || status;
  const isSimulating = status === "simulating";
  const phaseNum = currentIdx >= 0 ? currentIdx + 1 : 0;
  const phaseTotal = PHASE_ORDER.length;
  const overallPct = (() => {
    if (currentIdx < 0) return 5;
    if (isSimulating && total > 0) {
      // Per-agent granularity inside the simulating phase
      const base = (PHASE_ORDER.indexOf("simulating") / phaseTotal) * 100;
      const slice = (1 / phaseTotal) * 100;
      return base + slice * Math.min(1, completed / total);
    }
    return ((currentIdx + 0.5) / phaseTotal) * 100;
  })();

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 space-y-3">
      {/* Top line: phase label + elapsed */}
      <div className="flex items-center justify-between text-sm gap-3 flex-wrap">
        <span className="font-medium">{phaseLabel}</span>
        <span className="text-neutral-600 text-xs flex items-center gap-3">
          {phaseNum > 0 && (
            <span>
              Phase <span className="font-mono">{phaseNum}/{phaseTotal}</span>
            </span>
          )}
          {isSimulating && (
            <span className="font-mono">
              {completed} / {total} agents
            </span>
          )}
          <span className="font-mono text-neutral-500">{formatElapsed(elapsedMs)}</span>
        </span>
      </div>

      {/* Continuous progress bar */}
      <div className="h-1.5 bg-neutral-200 rounded-full overflow-hidden">
        <div
          className={`h-full bg-amber-500 transition-all ${isSimulating ? "" : "animate-pulse"}`}
          style={{ width: `${overallPct}%` }}
        />
      </div>

      {/* Phase chips — current = solid, past = checked, future = ghost */}
      <div className="flex flex-wrap gap-1.5">
        {PHASE_ORDER.map((p, i) => {
          const isPast = i < currentIdx;
          const isCurrent = i === currentIdx;
          return (
            <span
              key={p}
              className={[
                "text-[11px] px-2 py-0.5 rounded-full border font-medium",
                isCurrent && "bg-amber-500 text-white border-amber-500",
                isPast && "bg-neutral-200 text-neutral-600 border-neutral-200",
                !isCurrent && !isPast && "bg-white text-neutral-400 border-neutral-200",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {isPast ? "✓ " : ""}
              {PHASE_SHORT[p] || p}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function VariantCard({ runId, which, winner }: { runId: string; which: "a" | "b"; winner: boolean }) {
  return (
    <div className={`rounded-lg border-2 bg-white p-3 ${winner ? "border-emerald-500" : "border-neutral-200"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Variant {which.toUpperCase()}</span>
        {winner && <span className="text-xs bg-emerald-500 text-white px-2 py-0.5 rounded">winner</span>}
      </div>
      <a href={`/api/runs/${runId}/image/${which}`} target="_blank" rel="noopener noreferrer">
        <img
          src={`/api/runs/${runId}/image/${which}`}
          alt={`Variant ${which}`}
          className="w-full h-56 object-contain bg-neutral-50 rounded hover:opacity-90 transition cursor-zoom-in"
        />
      </a>
    </div>
  );
}