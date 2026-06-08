"""BiasAuditor v0.3 — the trust gate, redesigned for resonance.

Position-bias checks are gone (structurally impossible: agents see one variant).
New checks operate on the cohort + resonance vectors:

1. Cohort balance — counts per cohort and per (segment × cohort)
2. Per-dimension variance — low variance signals the LLM collapsed to a default
3. Mean-resonance inflation — flag when overall > 8.5 across both cohorts
4. Confidence collapse — too many low-confidence responses
5. Rationale coherence — does the rationale support the resonance scores?
"""
from __future__ import annotations
import logging
from collections import defaultdict

from .. import state
from ..llm import MODEL_FLASH, generate
from ..models import AuditReport, RESONANCE_DIMS, SimResult

log = logging.getLogger(__name__)


COHERENCE_PROMPT = """\
For each (overall_resonance_score, rationale) pair below, score whether the
rationale supports the overall score. Return a JSON array of scores 0.0–1.0
in the same order. 1.0 = rationale clearly justifies the score.
0.0 = rationale contradicts or is unrelated.

PAIRS:
{pairs}

Respond with ONLY: {{"scores": [0.9, 0.7, ...]}}
"""

INFLATION_THRESHOLD = 8.5
LOW_VARIANCE_THRESHOLD = 0.5
# Mid-range guard for collapse detection. Low variance is only suspicious when
# the mean sits in the indeterminate middle. Uniformly low or uniformly high
# scores across personas are real cross-persona signal, not model collapse.
COLLAPSE_MIDRANGE_LOW = 4.0
COLLAPSE_MIDRANGE_HIGH = 7.0
COHORT_IMBALANCE_TOLERANCE = 0.2  # |cohort_a - cohort_b| / total agents


def _cohort_balance(results: list[SimResult]) -> dict[str, int]:
    out: dict[str, int] = {"variant_a": 0, "variant_b": 0}
    for r in results:
        out[r.cohort] += 1
    return out


def _cohort_persona_balance(results: list[SimResult]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"variant_a": 0, "variant_b": 0})
    for r in results:
        out[r.scenario_segment][r.cohort] += 1
    return {k: dict(v) for k, v in out.items()}


def _per_dim_stats(results: list[SimResult]) -> dict[str, dict[str, float]]:
    """{dim: {mean, variance}} for every resonance dim."""
    out: dict[str, dict[str, float]] = {}
    n = len(results)
    if n == 0:
        return {dim: {"mean": 0.0, "variance": 0.0} for dim in RESONANCE_DIMS}
    for dim in RESONANCE_DIMS:
        scores = [r.resonance.get(dim, 5) for r in results]
        mean = sum(scores) / n
        var = sum((s - mean) ** 2 for s in scores) / n
        out[dim] = {"mean": round(mean, 3), "variance": round(var, 3)}
    return out


def _collapsed_dims(stats: dict[str, dict[str, float]]) -> list[str]:
    """Dims where low variance is suspicious (not explained by mean-extreme signal)."""
    return [
        dim
        for dim, s in stats.items()
        if s["variance"] < LOW_VARIANCE_THRESHOLD
        and COLLAPSE_MIDRANGE_LOW <= s["mean"] <= COLLAPSE_MIDRANGE_HIGH
    ]


def _segment_divergence(results: list[SimResult]) -> dict[str, dict[str, int]]:
    """{segment: {variant_a_count, variant_b_count}} from intent_signal."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        out[r.scenario_segment][r.intent_signal] += 1
    return {k: dict(v) for k, v in out.items()}


async def _score_coherence(results: list[SimResult]) -> float:
    """LLM-as-judge on (overall_resonance, rationale) pairs. One call."""
    if not results:
        return 1.0
    pairs_text = "\n".join(
        f"{i+1}. overall={r.resonance_overall:.1f} | rationale={r.rationale[:300]}"
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
        return 1.0  # fail open


def _build_warnings(
    cohort_balance: dict[str, int],
    collapsed_dims: list[str],
    inflation: bool,
    low_conf_rate: float,
    coherence: float,
    single_screen: bool = False,
) -> list[str]:
    warnings: list[str] = []
    total = sum(cohort_balance.values())
    if total > 0 and not single_screen:
        diff = abs(cohort_balance["variant_a"] - cohort_balance["variant_b"])
        if diff / total > COHORT_IMBALANCE_TOLERANCE:
            warnings.append(
                f"Cohort imbalance: variant_a={cohort_balance['variant_a']} vs "
                f"variant_b={cohort_balance['variant_b']}. Compare with care."
            )
    if collapsed_dims:
        warnings.append(
            f"Score collapse on {', '.join(collapsed_dims)}: agents gave nearly "
            f"identical mid-range answers across personas, suggesting the LLM "
            f"defaulted rather than evaluated for those dimensions."
        )
    if inflation:
        warnings.append(
            f"Resonance inflation: both cohorts averaged > {INFLATION_THRESHOLD}/10. "
            f"LLM agreeableness suspected — relative gap is still informative, "
            f"absolute scores are not."
        )
    if low_conf_rate > 0.4:
        warnings.append(
            f"{low_conf_rate:.0%} of agents reported low confidence. The page may "
            f"be ambiguous for these personas — fix obvious clarity issues first."
        )
    if coherence < 0.7:
        warnings.append(
            f"Rationale coherence is {coherence:.0%}. Some scores aren't well "
            f"justified by the agents' own reasoning."
        )
    return warnings


def _trust_level(
    cohort_balance: dict[str, int],
    inflation: bool,
    low_conf_rate: float,
    coherence: float,
    collapsed_dim_count: int,
    single_screen: bool = False,
) -> str:
    total = sum(cohort_balance.values())
    cohort_skew = 0.0 if single_screen else (
        (abs(cohort_balance["variant_a"] - cohort_balance["variant_b"]) / total) if total else 0
    )
    if inflation or low_conf_rate > 0.5 or coherence < 0.5 or collapsed_dim_count >= 3:
        return "low"
    if (
        cohort_skew > COHORT_IMBALANCE_TOLERANCE
        or low_conf_rate > 0.3
        or coherence < 0.75
        or collapsed_dim_count >= 1
    ):
        return "medium"
    return "high"


async def run(run_id: str) -> AuditReport:
    await state.set_status(run_id, "auditing")

    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")
    results = run.simulation_results
    if not results:
        raise ValueError("No simulation results to audit")

    single_screen = not run.variant_b_path
    cohort_balance = _cohort_balance(results)
    cohort_persona_balance = _cohort_persona_balance(results)
    dim_stats = _per_dim_stats(results)
    per_dim_var = {dim: s["variance"] for dim, s in dim_stats.items()}
    seg_div = _segment_divergence(results)

    overall_mean = sum(r.resonance_overall for r in results) / len(results)
    inflation = overall_mean > INFLATION_THRESHOLD

    low_conf_rate = sum(1 for r in results if r.confidence == "low") / len(results)
    coherence = await _score_coherence(results)

    collapsed_dims = _collapsed_dims(dim_stats)
    collapsed_dim_count = len(collapsed_dims)
    trust = _trust_level(cohort_balance, inflation, low_conf_rate, coherence, collapsed_dim_count, single_screen)
    warnings = _build_warnings(cohort_balance, collapsed_dims, inflation, low_conf_rate, coherence, single_screen)

    recommended_action = {
        "high":   "Results are reliable. Proceed with confidence.",
        "medium": "Results are directional. Validate before scaling traffic.",
        "low":    "Results are unreliable. Address the warnings before acting.",
    }[trust]

    audit = AuditReport(
        trust_level=trust,
        confidence_collapse=low_conf_rate > 0.4,
        low_confidence_rate=round(low_conf_rate, 3),
        avg_rationale_coherence=round(coherence, 3),
        segment_divergence=seg_div,
        cohort_balance=cohort_balance,
        cohort_persona_balance=cohort_persona_balance,
        per_dim_variance=per_dim_var,
        inflation_warning=inflation,
        warnings=warnings,
        recommended_action=recommended_action,
    )

    await state.write_audit(run_id, audit)
    log.info(
        f"[{run_id}] bias_auditor: trust={trust} "
        f"cohort=({cohort_balance['variant_a']}/{cohort_balance['variant_b']}) "
        f"overall_mean={overall_mean:.2f} low_conf={low_conf_rate:.2f} "
        f"coherence={coherence:.2f} collapsed_dims={collapsed_dim_count}"
    )
    return audit
