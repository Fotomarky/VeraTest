"""Synthesizer v0.3 — cohort-resonance aggregation.

Replaces the vote-based winner with a gap-and-significance verdict:
- compute mean resonance vector per cohort
- collapse to overall via RESONANCE_WEIGHTS
- declare a directional winner only if the gap is large enough vs. pooled noise
- friction clustering partitions by cohort (losing/winning)
- per-persona resonance matrix kept for the diagnostic heatmap
"""
from __future__ import annotations
import logging
import math
from collections import Counter, defaultdict

from .. import state
from ..llm import MODEL_FLASH, generate
from ..models import (
    FrictionTheme, RESONANCE_DIMS, RESONANCE_WEIGHTS, ScenarioCard, SimResult, Synthesis,
)

log = logging.getLogger(__name__)


CLUSTER_PROMPT = """\
Below are {kind} reported by simulated users evaluating a landing page.
Cluster them into 3-5 distinct themes. Each theme should be specific and
actionable (not generic like "page is bad").

For each theme, pick 1-2 example quotes from the raw list that best illustrate it.

{kind} (one per line, possibly with duplicates):
{lines}

Respond with ONLY a JSON object:
{{
  "themes": [
    {{
      "theme": "Specific, actionable description",
      "count": 7,
      "severity": "high" | "medium" | "low",
      "example_quotes": ["...", "..."]
    }}
  ]
}}
Severity = high if the theme would block conversion, medium if it would slow
research, low if it is just minor friction.
"""


SUMMARY_PROMPT = """\
Write a one-sentence executive summary and a 2-sentence recommendation for this
A/B pretest result.

DIRECTIONAL WINNER:  {winner}
RESONANCE GAP:       {gap:+.2f} (variant_b minus variant_a, on a 1-10 scale)
GAP SIGNIFICANCE:    {significance}
TRUST LEVEL:         {trust}
COHORT OVERALL:      variant_a = {a_overall:.2f}, variant_b = {b_overall:.2f}
TOP FRICTION THEMES (in the losing variant):
{themes}

Phrase carefully: this measures persona-page RESONANCE, which is a necessary
but not sufficient condition for conversion. Do NOT claim a predicted
conversion rate. Use language like "directionally favors X" or "resonates
more strongly with Y persona".

Respond with ONLY: {{"one_line": "...", "recommendation": "..."}}
"""


TIE_GAP_FLOOR = 0.3        # absolute |gap| below this -> tie regardless of std
STRONG_GAP_FLOOR = 0.8     # absolute |gap| floor for "strong" significance


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _partition_by_cohort(results: list[SimResult]) -> dict[str, list[SimResult]]:
    out: dict[str, list[SimResult]] = {"variant_a": [], "variant_b": []}
    for r in results:
        out[r.cohort].append(r)
    return out


def _cohort_resonance(by_cohort: dict[str, list[SimResult]]) -> dict[str, dict[str, float]]:
    """{cohort: {dim: mean_score}} per dim."""
    out: dict[str, dict[str, float]] = {}
    for cohort, items in by_cohort.items():
        if not items:
            out[cohort] = {dim: 0.0 for dim in RESONANCE_DIMS}
            continue
        dim_means: dict[str, float] = {}
        for dim in RESONANCE_DIMS:
            scores = [r.resonance.get(dim, 5) for r in items]
            dim_means[dim] = round(sum(scores) / len(scores), 2)
        out[cohort] = dim_means
    return out


def _cohort_overall(cohort_res: dict[str, dict[str, float]]) -> dict[str, float]:
    """Weighted mean across dims using RESONANCE_WEIGHTS."""
    out: dict[str, float] = {}
    for cohort, dim_means in cohort_res.items():
        total_w = sum(RESONANCE_WEIGHTS.get(d, 0) for d in dim_means)
        if total_w == 0:
            out[cohort] = 0.0
            continue
        weighted = sum(dim_means[d] * RESONANCE_WEIGHTS.get(d, 0) for d in dim_means)
        out[cohort] = round(weighted / total_w, 2)
    return out


def _pop_variance(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _pooled_std(by_cohort: dict[str, list[SimResult]]) -> float:
    """sqrt of mean of within-cohort variances on resonance_overall."""
    vars_ = []
    for items in by_cohort.values():
        if items:
            vars_.append(_pop_variance([r.resonance_overall for r in items]))
    if not vars_:
        return 0.0
    return math.sqrt(sum(vars_) / len(vars_))


def _verdict(gap: float, pooled_std: float) -> tuple[str, str]:
    """Returns (directional_winner, gap_significance)."""
    abs_gap = abs(gap)
    if abs_gap < TIE_GAP_FLOOR or abs_gap < pooled_std:
        return "tie", "tie"
    winner = "variant_b" if gap > 0 else "variant_a"
    if abs_gap > 1.5 * pooled_std and abs_gap > STRONG_GAP_FLOOR:
        return winner, "strong"
    if abs_gap > pooled_std:
        return winner, "moderate"
    return winner, "weak"


def _per_persona_resonance(
    results: list[SimResult],
) -> dict[str, dict[str, dict[str, float]]]:
    """{segment: {variant_a/b: {dim: mean_score}}}"""
    buckets: dict[str, dict[str, list[SimResult]]] = defaultdict(
        lambda: {"variant_a": [], "variant_b": []}
    )
    for r in results:
        buckets[r.scenario_segment][r.cohort].append(r)

    out: dict[str, dict[str, dict[str, float]]] = {}
    for segment, by_cohort in buckets.items():
        out[segment] = {}
        for cohort, items in by_cohort.items():
            if not items:
                continue
            dim_means: dict[str, float] = {}
            for dim in RESONANCE_DIMS:
                scores = [r.resonance.get(dim, 5) for r in items]
                dim_means[dim] = round(sum(scores) / len(scores), 2)
            out[segment][cohort] = dim_means
    return out


def _segment_splits(results: list[SimResult]) -> dict[str, dict[str, float]]:
    """{segment: {variant_a: overall_mean, variant_b: overall_mean}}"""
    buckets: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"variant_a": [], "variant_b": []}
    )
    for r in results:
        buckets[r.scenario_segment][r.cohort].append(r.resonance_overall)
    out: dict[str, dict[str, float]] = {}
    for segment, by_cohort in buckets.items():
        out[segment] = {
            cohort: round(sum(scores) / len(scores), 2) if scores else 0.0
            for cohort, scores in by_cohort.items()
        }
    return out


def _coverage_score(scenarios: list[ScenarioCard], results: list[SimResult]) -> int:
    if not results:
        return 0
    n = len(results)
    segments = {s.scenario_segment for s in results}
    devices = {next((sc.device for sc in scenarios if sc.id == s.scenario_id), "?") for s in results}
    styles = {next((sc.decision_style for sc in scenarios if sc.id == s.scenario_id), "?") for s in results}
    diversity = (len(segments) + len(devices) + len(styles)) / (3 * min(n, 6))
    return min(100, int(diversity * 100))


def _collect_trust_gaps(results: list[SimResult]) -> list[str]:
    counter: Counter[str] = Counter()
    for r in results:
        for signal in r.trust_signals_missing:
            s = signal.strip()
            if s:
                counter[s] += 1
    return [item for item, _ in counter.most_common(5)]


async def _cluster_friction(
    items: list[SimResult],
    field: str,
    kind_label: str,
) -> list[FrictionTheme]:
    """One LLM call to cluster either friction_points or what_worked into themes."""
    lines = []
    for r in items:
        for f in getattr(r, field):
            lines.append(f"- {f}")
    if not lines:
        return []
    raw = await generate(
        model=MODEL_FLASH,
        prompt=CLUSTER_PROMPT.format(kind=kind_label, lines="\n".join(lines[:200])),
        response_schema={},
        temperature=0.2,
    )
    themes_data = raw.get("themes", [])
    themes: list[FrictionTheme] = []
    for t in themes_data:
        try:
            themes.append(FrictionTheme(
                theme=t["theme"],
                count=int(t.get("count", 0)),
                severity=t.get("severity", "medium"),
                example_quotes=t.get("example_quotes", []),
            ))
        except Exception as e:
            log.warning(f"Theme parse failed: {e}")
    return sorted(themes, key=lambda t: t.count, reverse=True)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

async def run(run_id: str) -> Synthesis:
    run = await state.get_run(run_id)
    if run is None or run.audit is None:
        raise ValueError(f"Run {run_id} not ready for synthesis")

    await state.set_status(run_id, "synthesizing")

    results = run.simulation_results
    by_cohort = _partition_by_cohort(results)

    cohort_res = _cohort_resonance(by_cohort)
    cohort_overall = _cohort_overall(cohort_res)
    gap = round(cohort_overall.get("variant_b", 0.0) - cohort_overall.get("variant_a", 0.0), 3)
    pooled = _pooled_std(by_cohort)
    directional_winner, gap_significance = _verdict(gap, pooled)

    per_persona = _per_persona_resonance(results)
    segments = _segment_splits(results)
    coverage = _coverage_score(run.scenarios, results)
    trust_gaps = _collect_trust_gaps(results)

    # Cluster friction (losing cohort) and what_worked (winning cohort).
    if directional_winner == "tie":
        losing_items = results
        winning_items = results
    else:
        winning_items = by_cohort[directional_winner]
        losing_items = by_cohort[
            "variant_a" if directional_winner == "variant_b" else "variant_b"
        ]
    top_friction = await _cluster_friction(losing_items, "friction_points", "FRICTION POINTS")
    worked_themes = await _cluster_friction(winning_items, "what_worked", "WHAT WORKED")

    confound_warning: str | None = None
    if run.brief and run.brief.needs_clarification and run.brief.notes:
        confound_warning = run.brief.notes

    summary_raw = await generate(
        model=MODEL_FLASH,
        prompt=SUMMARY_PROMPT.format(
            winner=directional_winner,
            gap=gap,
            significance=gap_significance,
            trust=run.audit.trust_level,
            a_overall=cohort_overall.get("variant_a", 0.0),
            b_overall=cohort_overall.get("variant_b", 0.0),
            themes="\n".join(f"- {t.theme} ({t.count})" for t in top_friction[:3]) or "- (none)",
        ),
        response_schema={},
        temperature=0.4,
    )

    synthesis = Synthesis(
        cohort_resonance=cohort_res,
        cohort_resonance_overall=cohort_overall,
        resonance_gap=gap,
        directional_winner=directional_winner,
        gap_significance=gap_significance,
        per_persona_resonance=per_persona,
        coverage_score=coverage,
        top_friction=top_friction[:5],
        what_worked_themes=worked_themes[:5],
        segment_splits=segments,
        recommendation=summary_raw.get("recommendation", ""),
        one_line_summary=summary_raw.get("one_line", ""),
        confound_warning=confound_warning,
        trust_signal_gaps=trust_gaps,
    )

    await state.write_synthesis(run_id, synthesis)
    log.info(
        f"[{run_id}] synthesizer: winner={directional_winner} sig={gap_significance} "
        f"gap={gap:+.2f} pooled_std={pooled:.2f} a={cohort_overall.get('variant_a', 0):.2f} "
        f"b={cohort_overall.get('variant_b', 0):.2f} coverage={coverage}"
    )
    return synthesis
