"""Pipeline orchestrator.

Runs the five agents in sequence (with the simulator phase running its 20
sub-agents in parallel, capped at SIMAB_SIM_CONCURRENCY). Each agent
communicates by reading/writing shared state — no parameters passed between
phases.
"""
from __future__ import annotations
import asyncio
import logging

from . import state
from .agents import auditor, narrative, normalizer, scenarios, simulator, synthesizer
from .config import CONFIG

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
    """Top-level entrypoint. Runs the five phases sequentially."""
    log.info(f"[{run_id}] pipeline start")
    try:
        await normalizer.run(run_id)
        await scenarios.run(run_id)
        await _run_simulators(run_id)
        await auditor.run(run_id)
        await synthesizer.run(run_id)
        await narrative.run(run_id)
        log.info(f"[{run_id}] pipeline complete")
        await _notify_completion(run_id)
    except Exception as e:
        log.exception(f"[{run_id}] pipeline failed: {e}")
        await state.set_status(run_id, "failed", error=str(e))
        raise


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
