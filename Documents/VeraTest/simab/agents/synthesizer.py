"""Synthesizer — produces the final weighted narrative.

Reads all sim results + the audit, computes weighted vote (by scenario
traffic_weight, not raw count), clusters friction themes, and writes the
final user-facing Synthesis to shared state.
"""
from __future__ import annotations
import logging
from collections import defaultdict

from .. import state
from ..llm import MODEL_FLASH, generate
from ..models import FrictionTheme, ScenarioCard, SimResult, Synthesis

log = logging.getLogger(__name__)


CLUSTER_PROMPT = """\
Below are friction points reported by simulated users evaluating a landing page.
Cluster them into 3-5 distinct themes. Each theme should be specific and
actionable (not generic like "page is bad").

For each theme, also pick 1-2 example quotes from the raw list that best
illustrate it.

FRICTION POINTS (one per line, possibly with duplicates):
{friction_lines}

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
Severity = high if the theme caused would_bounce outcomes, medium if would_research_more,
low if just minor friction.
"""


SUMMARY_PROMPT = """\
Write a 1-sentence executive summary and a 2-sentence recommendation given
this result.

WINNER: {winner}
WEIGHTED VOTE: {weighted_vote}
TRUST LEVEL: {trust}
TOP FRICTION THEMES:
{themes}

Respond with ONLY: {{"one_line": "...", "recommendation": "..."}}
"""


def _weight_lookup(scenarios: list[ScenarioCard]) -> dict[str, float]:
    """Map scenario_id → traffic_weight (used by all aggregation functions)."""
    return {sc.id: sc.traffic_weight for sc in scenarios}


def _compute_votes(
    results: list[SimResult], weights: dict[str, float]
) -> tuple[dict[str, int], dict[str, float]]:
    raw: dict[str, int] = defaultdict(int)
    weighted: dict[str, float] = defaultdict(float)
    for r in results:
        raw[r.verdict] += 1
        w = weights.get(r.scenario_id, 1.0 / len(results))
        weighted[r.verdict] += w
    total_w = sum(weighted.values()) or 1.0
    weighted_norm = {k: round(v / total_w, 3) for k, v in weighted.items()}
    return dict(raw), weighted_norm


def _winner(weighted: dict[str, float]) -> str:
    """Pick winner from weighted vote, ignoring neither/needs_more_info."""
    candidates = {
        k: v for k, v in weighted.items()
        if k in ("variant_a", "variant_b")
    }
    if not candidates:
        return "neither"
    # If margin is tiny (<5pp), call it neither
    sorted_v = sorted(candidates.values(), reverse=True)
    if len(sorted_v) >= 2 and sorted_v[0] - sorted_v[1] < 0.05:
        return "neither"
    return max(candidates, key=candidates.get)


def _coverage_score(scenarios: list[ScenarioCard], results: list[SimResult]) -> int:
    """0-100 score based on segment + device + decision-style diversity."""
    if not results:
        return 0
    n = len(results)
    segments = {s.scenario_segment for s in results}
    devices = {next((sc.device for sc in scenarios if sc.id == s.scenario_id), "?") for s in results}
    styles = {next((sc.decision_style for sc in scenarios if sc.id == s.scenario_id), "?") for s in results}
    diversity = (len(segments) + len(devices) + len(styles)) / (3 * min(n, 6))
    return min(100, int(diversity * 100))


def _segment_split_pct(results: list[SimResult]) -> dict[str, dict[str, float]]:
    """{segment: {variant_a: 0.7, variant_b: 0.3, ...}}"""
    out: dict[str, dict[str, float]] = {}
    by_seg: dict[str, list[SimResult]] = defaultdict(list)
    for r in results:
        by_seg[r.scenario_segment].append(r)
    for seg, items in by_seg.items():
        votes: dict[str, int] = defaultdict(int)
        for r in items:
            votes[r.verdict] += 1
        total = len(items)
        out[seg] = {k: round(v / total, 3) for k, v in votes.items()}
    return out


def _compute_visual_impact(
    results: list[SimResult], weights: dict[str, float]
) -> dict[str, float]:
    """Weighted average visual_impact score per variant.

    Returns {"variant_a": 6.8, "variant_b": 7.2}. Returns 0.0 where no
    agent reported a score (backward compat with pre-v0.2 runs).
    """
    totals: dict[str, float] = {"variant_a": 0.0, "variant_b": 0.0}
    weight_sums: dict[str, float] = {"variant_a": 0.0, "variant_b": 0.0}
    for r in results:
        w = weights.get(r.scenario_id, 1.0 / max(len(results), 1))
        for variant, score in r.visual_impact.items():
            if variant in totals:
                totals[variant] += float(score) * w
                weight_sums[variant] += w
    return {
        v: round(totals[v] / weight_sums[v], 1) if weight_sums[v] > 0 else 0.0
        for v in ("variant_a", "variant_b")
    }


def _compute_fogg_averages(
    results: list[SimResult], weights: dict[str, float]
) -> dict[str, dict[str, float]]:
    """Weighted-average Fogg B=MAP scores grouped by the variant each agent chose.

    Returns:
      {
        "variant_a": {"motivation": 6.2, "ability": 5.0},
        "variant_b": {"motivation": 7.1, "ability": 8.3},
      }
    Agents that voted "neither" or "needs_more_info" are excluded.
    """
    buckets: dict[str, dict[str, list[tuple[float, float]]]] = {
        "variant_a": {"motivation": [], "ability": []},
        "variant_b": {"motivation": [], "ability": []},
    }
    for r in results:
        if r.verdict not in buckets:
            continue
        w = weights.get(r.scenario_id, 1.0 / max(len(results), 1))
        if r.fogg_motivation > 0:
            buckets[r.verdict]["motivation"].append((r.fogg_motivation, w))
        if r.fogg_ability > 0:
            buckets[r.verdict]["ability"].append((r.fogg_ability, w))

    out: dict[str, dict[str, float]] = {}
    for variant, dims in buckets.items():
        agg: dict[str, float] = {}
        for dim, pairs in dims.items():
            if pairs:
                total = sum(v * w for v, w in pairs)
                wsum = sum(w for _, w in pairs)
                agg[dim] = round(total / wsum, 1) if wsum > 0 else 0.0
        if agg:
            out[variant] = agg
    return out


def _collect_trust_gaps(results: list[SimResult]) -> list[str]:
    """Return trust signals most commonly reported as MISSING, sorted by frequency.

    Returns the top 5 gaps as a list of strings.
    """
    from collections import Counter
    counter: Counter[str] = Counter()
    for r in results:
        for signal in r.trust_signals_missing:
            s = signal.strip()
            if s:
                counter[s] += 1
    return [item for item, _ in counter.most_common(5)]


async def _cluster_friction(results: list[SimResult], kind: str = "friction_points") -> list[FrictionTheme]:
    """Cluster friction_points or what_worked into themes via one LLM call."""
    lines = []
    for r in results:
        for f in getattr(r, kind):
            lines.append(f"- {f}")
    if not lines:
        return []

    raw = await generate(
        model=MODEL_FLASH,
        prompt=CLUSTER_PROMPT.format(friction_lines="\n".join(lines[:200])),
        response_schema={},
        temperature=0.2,
    )
    themes_data = raw.get("themes", [])
    themes = []
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


async def run(run_id: str) -> Synthesis:
    run = await state.get_run(run_id)
    if run is None or run.audit is None:
        raise ValueError(f"Run {run_id} not ready for synthesis")

    await state.set_status(run_id, "synthesizing")

    weights = _weight_lookup(run.scenarios)
    raw_vote, weighted_vote = _compute_votes(run.simulation_results, weights)
    winner = _winner(weighted_vote)

    # Filter friction to the LOSING variant's reports (most actionable)
    losing = "variant_a" if winner == "variant_b" else "variant_b"
    losing_results = [r for r in run.simulation_results if r.verdict == winner]
    top_friction = await _cluster_friction(losing_results, "friction_points")
    worked_themes = await _cluster_friction(
        [r for r in run.simulation_results if r.verdict == winner], "what_worked"
    )

    coverage = _coverage_score(run.scenarios, run.simulation_results)
    segments = _segment_split_pct(run.simulation_results)

    weights = _weight_lookup(run.scenarios or [])
    visual_impact = _compute_visual_impact(run.simulation_results, weights)
    fogg_avg = _compute_fogg_averages(run.simulation_results, weights)
    trust_signal_gaps = _collect_trust_gaps(run.simulation_results)

    confound_warning: str | None = None
    if run.brief and run.brief.needs_clarification and run.brief.notes:
        confound_warning = run.brief.notes

    # One-line summary + recommendation
    summary_raw = await generate(
        model=MODEL_FLASH,
        prompt=SUMMARY_PROMPT.format(
            winner=winner,
            weighted_vote=weighted_vote,
            trust=run.audit.trust_level,
            themes="\n".join(f"- {t.theme} ({t.count})" for t in top_friction[:3]),
        ),
        response_schema={},
        temperature=0.4,
    )

    synthesis = Synthesis(
        winner=winner,
        raw_vote=raw_vote,
        weighted_vote=weighted_vote,
        coverage_score=coverage,
        top_friction=top_friction[:5],
        what_worked_themes=worked_themes[:5],
        segment_splits=segments,
        recommendation=summary_raw.get("recommendation", ""),
        one_line_summary=summary_raw.get("one_line", ""),
        visual_impact=visual_impact,
        confound_warning=confound_warning,
        fogg_avg=fogg_avg,
        trust_signal_gaps=trust_signal_gaps,
    )

    await state.write_synthesis(run_id, synthesis)
    log.info(f"[{run_id}] synthesizer: winner={winner} coverage={coverage} "
             f"themes={len(top_friction)}")
    return synthesis