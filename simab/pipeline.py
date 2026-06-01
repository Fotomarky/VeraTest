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
from .integrations.session import run_session

log = logging.getLogger(__name__)


async def _run_simulators(run_id: str) -> None:
    """Fan out 20 sim agents with bounded concurrency."""
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
                # Continue — partial results are still useful

    await asyncio.gather(*[
        _bounded(i, sc) for i, sc in enumerate(run.scenarios)
    ])

    completed = await state.count_sim_results(run_id)
    log.info(f"[{run_id}] simulators: {completed}/{len(run.scenarios)} complete")


async def run_pipeline(run_id: str) -> None:
    """Top-level entrypoint. Runs the user-visible phases sequentially, then
    fires fidelity as a background task so the user-visible report lands
    ~60s sooner. The Phoenix annotations + drift dataset are enriched
    asynchronously and the fidelity slice is written when ready."""
    log.info(f"[{run_id}] pipeline start")
    try:
        with run_session(run_id):
            await normalizer.run(run_id)
            await scenarios.run(run_id)
            await _run_simulators(run_id)
            await auditor.run(run_id)
            await synthesizer.run(run_id)
            await narrative.run(run_id)
            await state.set_status(run_id, "complete")
        log.info(f"[{run_id}] pipeline complete")
        await _notify_completion(run_id)
        asyncio.create_task(_run_fidelity_async(run_id))
    except Exception as e:
        log.exception(f"[{run_id}] pipeline failed: {e}")
        await state.set_status(run_id, "failed", error=str(e))
        raise
    finally:
        ratelimit.notify_run_finished()


async def _run_fidelity_async(run_id: str) -> None:
    """Run fidelity off the critical path. Never touches run.status — the
    run is already 'complete' before this fires. Failures are logged but
    do not surface to the user."""
    try:
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
