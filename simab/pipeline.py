"""Pipeline orchestrator.

Runs the five agents in sequence (with the simulator phase running its 20
sub-agents in parallel, capped at SIMAB_SIM_CONCURRENCY). Each agent
communicates by reading/writing shared state — no parameters passed between
phases.
"""
from __future__ import annotations
import asyncio
import logging

from . import ratelimit, state
from .agents import (
    auditor, fidelity, narrative, normalizer, scenarios, simulator, synthesizer,
)
from .config import CONFIG
from .integrations.phoenix import pipeline_span
from .integrations.session import mark_session_success, run_session

log = logging.getLogger(__name__)


async def _run_simulators(run_id: str) -> None:
    """Fan out 20 sim agents with bounded concurrency, then enforce a quorum.

    Failed sims get one retry pass (writes are idempotent upserts, so re-running
    an index is harmless). If fewer than SIMAB_SIM_QUORUM of the panel completed
    after that, raise — synthesizing a verdict from a thin panel produces a
    misleading "tie" that looks like a finding (this is what turned Gemini 503
    bursts into silent abstentions in validation).
    """
    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    await state.set_status(run_id, "simulating")
    sem = asyncio.Semaphore(CONFIG.sim_concurrency)

    async def _bounded(agent_idx: int, scenario):
        async with sem:
            try:
                await simulator.run_one(run_id, agent_idx, scenario)
            except Exception as e:
                log.error(f"[{run_id}] agent {agent_idx} failed: {e}")
                # Continue — the retry pass below picks up the stragglers

    async def _missing_indices() -> list[int]:
        fresh = await state.get_run(run_id)
        done = {r.agent_idx for r in (fresh.simulation_results or [])}
        return [i for i in range(len(run.scenarios)) if i not in done]

    await asyncio.gather(*[
        _bounded(i, sc) for i, sc in enumerate(run.scenarios)
    ])

    missing = await _missing_indices()
    if missing:
        log.warning(f"[{run_id}] retrying {len(missing)} failed sims: {missing}")
        await asyncio.gather(*[
            _bounded(i, run.scenarios[i]) for i in missing
        ])

    completed = await state.count_sim_results(run_id)
    total = len(run.scenarios)
    log.info(f"[{run_id}] simulators: {completed}/{total} complete")
    if total and completed / total < CONFIG.sim_quorum:
        raise RuntimeError(
            f"Only {completed}/{total} simulations completed "
            f"(quorum {CONFIG.sim_quorum:.0%}) — refusing to synthesize a "
            f"verdict from a thin panel. Likely Gemini capacity (503s); "
            f"retry the run."
        )


async def run_pipeline(run_id: str) -> None:
    """Top-level entrypoint. Runs the user-visible phases sequentially, then
    fires fidelity as a background task so the user-visible report lands
    ~60s sooner. The Phoenix annotations + drift dataset are enriched
    asynchronously and the fidelity slice is written when ready."""
    log.info(f"[{run_id}] pipeline start")
    try:
        with run_session(run_id, input_text=await _session_input(run_id)) as session_span:
            with pipeline_span("phase.study_designer"):
                await normalizer.run(run_id)
            with pipeline_span("phase.panel_recruiter"):
                await scenarios.run(run_id)
            with pipeline_span("phase.cognitive_walkers"):
                await _run_simulators(run_id)
            # Audit + synthesize concurrently. The synthesizer's cluster work
            # doesn't need the audit; only its final summary call does. It
            # awaits `audit_task` internally just before that call, so audit
            # runs in parallel with the clustering for ~25s of wall savings.
            with pipeline_span("phase.audit_and_synthesis"):
                audit_task = asyncio.create_task(auditor.run(run_id))
                try:
                    await synthesizer.run(run_id, audit_task=audit_task)
                except Exception:
                    if not audit_task.done():
                        audit_task.cancel()
                    raise
                # Synth awaits the task internally, but guard against any path
                # that lets it return without consuming the result.
                if not audit_task.done():
                    await audit_task
            with pipeline_span("phase.report_narrators"):
                await narrative.run(run_id)
            await state.set_status(run_id, "complete")
            log.info(f"[{run_id}] pipeline complete")
            mark_session_success(session_span, await _session_output(run_id))
            await _notify_completion(run_id)
            # Created inside the session span so the background fidelity
            # phase joins the same trace tree (children may outlive the root).
            asyncio.create_task(_run_fidelity_async(run_id))
    except Exception as e:
        log.exception(f"[{run_id}] pipeline failed: {e}")
        await state.set_status(run_id, "failed", error=str(e))
        raise
    finally:
        ratelimit.notify_run_finished()


async def _session_input(run_id: str) -> str | None:
    """Goal + audience for the run root span's `input.value` — what the
    Phoenix trace table shows in its "input" column."""
    run = await state.get_run(run_id)
    if run is None:
        return None
    parts = [f"Goal: {run.goal}"]
    if run.audience_raw:
        parts.append(f"Audience: {run.audience_raw}")
    parts.append("Mode: A/B comparison" if run.variant_b_path else "Mode: single-screen")
    return "\n".join(parts)


async def _session_output(run_id: str) -> str | None:
    """Verdict summary for the run root span's `output.value`."""
    run = await state.get_run(run_id)
    syn = run.synthesis if run else None
    if syn is None:
        return None
    parts = [f"Directional winner: {syn.directional_winner}"]
    if syn.cohort_resonance_overall:
        scores = ", ".join(
            f"{cohort}={score:.1f}/10"
            for cohort, score in sorted(syn.cohort_resonance_overall.items())
            if score
        )
        if scores:
            parts.append(f"Resonance: {scores}")
    if syn.recommendation:
        parts.append(syn.recommendation)
    return "\n".join(parts)


async def _run_fidelity_async(run_id: str) -> None:
    """Run fidelity off the critical path. Never touches run.status — the
    run is already 'complete' before this fires. Failures are logged but
    do not surface to the user."""
    try:
        with pipeline_span("phase.fidelity_auditor"):
            await fidelity.run(run_id)
    except Exception as e:
        log.warning(f"[{run_id}] fidelity (background) failed (non-fatal): {e}")


async def _notify_completion(run_id: str) -> None:
    """Best-effort post to Slack on completion. Failures don't break the run."""
    try:
        from .integrations.slack import post_run_to_slack
        run = await state.get_run(run_id)
        if run is None:
            return
        share_url = f"{CONFIG.frontend_url}/runs/{run_id}"
        await post_run_to_slack(run, share_url)
    except Exception as e:
        log.warning(f"[{run_id}] completion notification failed (non-fatal): {e}")
