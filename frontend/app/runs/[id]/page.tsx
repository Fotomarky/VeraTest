"use client";
import { useEffect, useState } from "react";
import PackmanTheater from "../../components/PackmanTheater";
import CommandRail from "../../components/CommandRail";
import WhatToDoNext from "../../components/WhatToDoNext";
import BlockersMatrix from "../../components/BlockersMatrix";
import PersonaCarousel from "../../components/PersonaCarousel";
import UserStoryScaffold from "../../components/UserStoryScaffold";
import VisualEvidence from "../../components/VisualEvidence";

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
  agent_idx: number;
  cohort: "variant_a" | "variant_b";
  resonance: Record<string, number>;
  resonance_overall: number;
  intent_signal: "would_act" | "would_research" | "would_leave";
  confidence: string;
  friction_points: string[];
  what_worked: string[];
  rationale: string;
  first_impression?: string;
  trust_signals_found?: string[];
  trust_signals_missing?: string[];
  metacognitive_reflection?: string;
};

type Run = {
  run_id: string;
  status: string;
  goal: string;
  variant_b_path?: string | null;
  scenarios?: ScenarioCard[];
  simulation_results?: SimResult[];
  audit?: { trust_level: string; warnings: string[]; recommended_action: string };
  synthesis?: {
    directional_winner: "variant_a" | "variant_b" | "tie";
    cohort_resonance_overall: Record<string, number>;
    cohort_resonance?: Record<string, Record<string, number>>;
    coverage_score: number;
    top_friction: Array<{
      theme: string;
      count: number;
      severity: "high" | "medium" | "low";
      example_quotes: Array<{ quote: string; agent_idx?: number | null; segment?: string | null }>;
      cohort?: "variant_a" | "variant_b" | "both";
    }>;
    what_worked_themes: Array<{
      theme: string;
      count: number;
      severity: "high" | "medium" | "low";
      example_quotes: Array<{ quote: string; agent_idx?: number | null; segment?: string | null }>;
      cohort?: "variant_a" | "variant_b" | "both";
    }>;
    one_line_summary?: string;
    recommendation?: string;
    confound_warning?: string;
    trust_signal_gaps?: string[];
  };
  fidelity?: {
    persona_consistency: number;
    agents_drifted: number;
    rationale_coherence?: number;
    agents_incoherent?: number;
    drifted_agent_indices?: number[];
  } | null;
  error?: string;
};

const PHASE_LABELS: Record<string, string> = {
  pending: "Queued — waiting for the orchestrator",
  normalizing: "Reading the brief — analysing variants and extracting personas",
  building_scenarios: "Building scenarios — assigning agents proportionally to traffic",
  simulating: "Running simulation agents in parallel",
  auditing: "Auditing — checking for bias and confidence collapse",
  synthesizing: "Synthesising final report — clustering friction themes",
  narrating: "Narrating — writing structural diff, hypothesis and cohort story",
  calibrating: "Calibrating — measuring persona fidelity (LLM-as-a-Judge)",
  complete: "Complete",
  failed: "Failed",
};

const PHASE_ORDER = [
  "pending",
  "normalizing",
  "building_scenarios",
  "simulating",
  "auditing",
  "synthesizing",
  "narrating",
  "calibrating",
] as const;

const PHASE_SHORT: Record<string, string> = {
  pending: "Queued",
  normalizing: "Brief",
  building_scenarios: "Scenarios",
  simulating: "Simulate",
  auditing: "Audit",
  synthesizing: "Synthesise",
  narrating: "Narrate",
  calibrating: "Calibrate",
};

function computeFoggAvg(results: SimResult[]): Record<string, Record<string, number>> {
  const sums: Record<string, Record<string, number>> = {};
  const counts: Record<string, number> = {};
  for (const r of results) {
    if (!sums[r.cohort]) { sums[r.cohort] = {}; counts[r.cohort] = 0; }
    for (const [dim, score] of Object.entries(r.resonance ?? {})) {
      sums[r.cohort][dim] = (sums[r.cohort][dim] ?? 0) + score;
    }
    counts[r.cohort]++;
  }
  const avgs: Record<string, Record<string, number>> = {};
  for (const [cohort, dims] of Object.entries(sums)) {
    avgs[cohort] = {};
    for (const [dim, total] of Object.entries(dims)) {
      avgs[cohort][dim] = total / counts[cohort];
    }
  }
  return avgs;
}

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
    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    // The fidelity slice is written by a background task a few seconds AFTER
    // the run flips to 'complete'. Keep polling briefly past completion so the
    // persona-fidelity badge appears without a manual refresh, but bound it so
    // we don't poll forever if Phoenix/fidelity never lands.
    let postCompletePolls = 0;
    const MAX_POST_COMPLETE_POLLS = 15;

    const stopPolling = () => {
      if (pollTimer !== null) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const startPolling = (intervalMs: number) => {
      if (pollTimer !== null) return;
      pollTimer = setInterval(async () => {
        if (cancelled) return;
        try {
          const res = await fetch(`/api/runs/${params.id}`);
          if (!res.ok) return;
          const data = await res.json();
          if (cancelled) return;
          setRun(data);
          if (data.status === "failed") {
            stopPolling();
          } else if (data.status === "complete") {
            if (data.fidelity != null || postCompletePolls >= MAX_POST_COMPLETE_POLLS) {
              stopPolling();
            } else {
              postCompletePolls++;
            }
          }
        } catch {}
      }, intervalMs);
    };

    // Initial fetch
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
    // Safety-net poll runs alongside SSE at a slow cadence. SSE delivers
    // sub-second updates when it's healthy; the poll catches silently-dropped
    // events on flaky paths (Cloud Run idle close, proxy buffering) so the
    // phase pill always catches up within a few seconds.
    startPolling(5000);
    source.onerror = () => {
      source.close();
      // SSE confirmed dead — speed up the poll so updates stay responsive.
      stopPolling();
      startPolling(2000);
    };

    return () => {
      cancelled = true;
      source.close();
      stopPolling();
    };
  }, [params.id]);

  useEffect(() => {
    if (run?.status === "complete" || run?.status === "failed") return;
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
          <h1 className="text-xl font-semibold">Connecting…</h1>
          <div className="text-xs font-mono text-neutral-400 mt-1">{params.id}</div>
        </div>
        <CommandRail
          synthesis={null}
          audit={null}
          runId={params.id}
          status="pending"
          onCopyMarkdown={copyMarkdown}
          copied={copied}
        />
      </div>
    );
  }

  const completed = run.simulation_results?.length ?? 0;
  const total = run.scenarios?.length ?? 20;
  const inProgress = run.status !== "complete" && run.status !== "failed";
  const synth = run.synthesis;
  const winner = synth?.directional_winner ?? "tie";
  const foggAvg = computeFoggAvg(run.simulation_results ?? []);
  const isSingleScreen = !run.variant_b_path;

  const scenariosBySegment = new Map<string, ScenarioCard>();
  for (const sc of run.scenarios ?? []) {
    if (!scenariosBySegment.has(sc.segment)) scenariosBySegment.set(sc.segment, sc);
  }
  const uniquePersonas = Array.from(scenariosBySegment.values());

  const resultsBySegment = new Map<string, SimResult[]>();
  for (const r of run.simulation_results ?? []) {
    const bucket = resultsBySegment.get(r.scenario_segment) ?? [];
    bucket.push(r);
    resultsBySegment.set(r.scenario_segment, bucket);
  }

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Title */}
      <div className="min-w-0">
        <h1 className="text-xl font-semibold truncate">{run.goal}</h1>
        <div className="text-xs font-mono text-neutral-400 mt-1">{run.run_id}</div>
      </div>

      <CommandRail
        synthesis={synth ?? null}
        audit={run.audit ?? null}
        fidelity={run.fidelity ?? null}
        totalAgents={run.simulation_results?.length ?? 0}
        runId={run.run_id}
        status={run.status}
        onCopyMarkdown={copyMarkdown}
        copied={copied}
      />

      {inProgress && (
        <PackmanTheater
          run={run}
          fallback={
            <ProgressBlock
              status={run.status}
              completed={completed}
              total={total}
              elapsedMs={now - mountedAt}
            />
          }
        />
      )}

      {run.status === "failed" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="font-medium mb-1">Run failed</div>
          <div className="text-xs font-mono break-all">{run.error ?? "unknown error"}</div>
        </div>
      )}

      {synth && (
        <WhatToDoNext
          topFriction={synth.top_friction ?? []}
          recommendation={synth.recommendation}
          foggAvg={foggAvg}
          winner={winner}
          simulationResults={run.simulation_results ?? []}
          confoundWarning={synth.confound_warning}
          totalAgents={run.simulation_results?.length ?? total}
          personaCount={uniquePersonas.length}
        />
      )}

      {synth && (
        <BlockersMatrix
          topFriction={synth.top_friction ?? []}
          whatWorkedThemes={synth.what_worked_themes ?? []}
          trustSignalGaps={synth.trust_signal_gaps ?? []}
          foggAvg={foggAvg}
          winner={winner}
          simulationResults={run.simulation_results ?? []}
          isSingleScreen={isSingleScreen}
        />
      )}

      {uniquePersonas.length > 0 && (
        <PersonaCarousel
          personas={uniquePersonas}
          resultsBySegment={resultsBySegment}
          winner={winner}
          isSingleScreen={isSingleScreen}
        />
      )}

      {synth && (
        <UserStoryScaffold
          topFriction={synth.top_friction ?? []}
          whatWorkedThemes={synth.what_worked_themes ?? []}
          goal={run.goal}
          resultsBySegment={resultsBySegment}
        />
      )}

      <VisualEvidence
        runId={run.run_id}
        winner={winner}
        visualImpact={{}}
        confoundWarning={synth?.confound_warning}
        isSingleScreen={isSingleScreen}
      />
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
  const phaseLabel = PHASE_LABELS[status] ?? status;
  const isSimulating = status === "simulating";
  const phaseNum = currentIdx >= 0 ? currentIdx + 1 : 0;
  const phaseTotal = PHASE_ORDER.length;
  const overallPct = (() => {
    if (currentIdx < 0) return 5;
    if (isSimulating && total > 0) {
      const base = (PHASE_ORDER.indexOf("simulating") / phaseTotal) * 100;
      const slice = (1 / phaseTotal) * 100;
      return base + slice * Math.min(1, completed / total);
    }
    return ((currentIdx + 0.5) / phaseTotal) * 100;
  })();

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 space-y-3">
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
      <div className="h-1.5 bg-neutral-200 rounded-full overflow-hidden">
        <div
          className={`h-full bg-amber-500 transition-all ${isSimulating ? "" : "animate-pulse"}`}
          style={{ width: `${overallPct}%` }}
        />
      </div>
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
              {PHASE_SHORT[p] ?? p}
            </span>
          );
        })}
      </div>
    </div>
  );
}

