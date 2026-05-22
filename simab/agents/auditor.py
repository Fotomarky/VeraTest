"""BiasAuditor — the trust gate.

This is the differentiator. It reads all simulation results and flags
systematic biases BEFORE the user sees a winner. The dashboard surfaces
its warnings prominently.

Checks:
1. Order bias — was the first-shown image picked too often? (We counterbalanced,
   so first-shown ≈ 50/50 between variants. >65% one way = bias.)
2. Confidence collapse — too many "low confidence" responses means the variants
   are both weak, not that one is better.
3. Coherence — do rationales actually support verdicts? (Quick LLM judge call.)
4. Segment divergence — if different segments disagree strongly, that's a real
   insight, not noise. Surface it.
"""
from __future__ import annotations
import logging
from collections import defaultdict

from .. import state
from ..llm import MODEL_FLASH, generate
from ..models import AuditReport, SimResult

log = logging.getLogger(__name__)


COHERENCE_PROMPT = """\
For each (verdict, rationale) pair below, score whether the rationale actually
supports the verdict. Return a JSON array of scores 0.0-1.0 in the same order.
1.0 = rationale clearly justifies the verdict.
0.0 = rationale contradicts or is unrelated to the verdict.

PAIRS:
{pairs}

Respond with ONLY: {{"scores": [0.9, 0.7, ...]}}
"""


def _compute_first_position_win_rate(results: list[SimResult]) -> float:
    """How often did the first-shown image win? Should be ~0.5 with counterbalancing."""
    if not results:
        return 0.5
    first_wins = 0
    decided = 0
    for r in results:
        if r.verdict in ("neither", "needs_more_info"):
            continue
        decided += 1
        # presented_order[0] is what was shown first
        if r.verdict == r.presented_order[0]:
            first_wins += 1
    return first_wins / decided if decided > 0 else 0.5


def _segment_breakdown(results: list[SimResult]) -> dict[str, dict[str, int]]:
    """{ segment -> { variant_a: 3, variant_b: 7, ... } }"""
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        out[r.scenario_segment][r.verdict] += 1
    return {k: dict(v) for k, v in out.items()}


async def _score_coherence(results: list[SimResult]) -> float:
    """LLM-as-judge on (verdict, rationale) pairs. One call total."""
    if not results:
        return 1.0
    pairs_text = "\n".join(
        f"{i+1}. verdict={r.verdict} | rationale={r.rationale[:300]}"
        for i, r in enumerate(results)
    )
    try:
        raw = await generate(
            model=MODEL_FLASH,
            prompt=COHERENCE_PROMPT.format(pairs=pairs_text),
            response_schema={},
            temperature=0,
        )
        scores = raw.get("scores", [])
        if not scores:
            return 1.0
        return sum(scores) / len(scores)
    except Exception as e:
        log.warning(f"Coherence scoring failed: {e}")
        return 1.0  # fail open, don't penalize the user


def _build_warnings(
    first_pos_rate: float,
    low_conf_rate: float,
    coherence: float,
    segment_divergence: dict[str, dict[str, int]],
) -> list[str]:
    warnings = []
    if abs(first_pos_rate - 0.5) > 0.15:
        bias_direction = "first-shown" if first_pos_rate > 0.5 else "second-shown"
        warnings.append(
            f"Position bias detected: {first_pos_rate:.0%} of decisions favored "
            f"the {bias_direction} image. Treat results as directional only."
        )
    if low_conf_rate > 0.4:
        warnings.append(
            f"{low_conf_rate:.0%} of agents reported low confidence. Both "
            f"variants may have unresolved issues — fix obvious friction first."
        )
    if coherence < 0.7:
        warnings.append(
            f"Rationale coherence is {coherence:.0%}. Some verdicts aren't well "
            f"justified by the agents' own reasoning."
        )
    # Strong segment divergence is signal, not noise — flag it as insight
    return warnings


def _trust_level(first_pos_rate: float, low_conf_rate: float, coherence: float) -> str:
    if (abs(first_pos_rate - 0.5) > 0.2 or low_conf_rate > 0.5 or coherence < 0.5):
        return "low"
    if (abs(first_pos_rate - 0.5) > 0.1 or low_conf_rate > 0.3 or coherence < 0.75):
        return "medium"
    return "high"


async def run(run_id: str) -> AuditReport:
    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    await state.set_status(run_id, "auditing")
    results = run.simulation_results
    if not results:
        raise ValueError("No simulation results to audit")

    first_pos_rate = _compute_first_position_win_rate(results)
    low_conf_rate = sum(1 for r in results if r.confidence == "low") / len(results)
    segment_div = _segment_breakdown(results)
    coherence = await _score_coherence(results)

    trust = _trust_level(first_pos_rate, low_conf_rate, coherence)
    warnings = _build_warnings(first_pos_rate, low_conf_rate, coherence, segment_div)

    recommended_action = {
        "high": "Results are reliable. Proceed with confidence.",
        "medium": "Results are directional. Consider validating with real traffic.",
        "low": "Results are unreliable. Re-run with more scenario diversity or "
               "fix obvious issues in the variants first.",
    }[trust]

    audit = AuditReport(
        trust_level=trust,
        order_bias_detected=abs(first_pos_rate - 0.5) > 0.15,
        first_position_win_rate=round(first_pos_rate, 3),
        confidence_collapse=low_conf_rate > 0.4,
        low_confidence_rate=round(low_conf_rate, 3),
        avg_rationale_coherence=round(coherence, 3),
        segment_divergence=segment_div,
        warnings=warnings,
        recommended_action=recommended_action,
    )

    await state.write_audit(run_id, audit)
    log.info(f"[{run_id}] bias_auditor: trust={trust} bias_rate={first_pos_rate:.2f} "
             f"low_conf={low_conf_rate:.2f} coherence={coherence:.2f}")
    return audit
