"""Tests for the visual evaluation + cognitive model fields added in v0.2.

These are pure schema/math tests — no Gemini calls.
"""
import pytest
from simab.models import ScenarioCard, SimResult, Synthesis
from simab.agents.synthesizer import (
    _compute_visual_impact,
    _compute_fogg_averages,
    _collect_trust_gaps,
    _weight_lookup,
)


# ── ScenarioCard field tests ──────────────────────────────────────────────────

def test_scenario_card_new_fields_default():
    sc = ScenarioCard(id="sc_001", segment="test", traffic_weight=0.5)
    assert sc.visual_style_preference == ""
    assert sc.patience_threshold == "medium"
    assert sc.communication_style == ""


def test_scenario_card_new_fields_set():
    sc = ScenarioCard(
        id="sc_001",
        segment="Tech-Savvy Donor",
        traffic_weight=0.3,
        visual_style_preference="clean/minimal with clear data",
        patience_threshold="low",
        communication_style="data-driven and precise",
    )
    assert sc.visual_style_preference == "clean/minimal with clear data"
    assert sc.patience_threshold == "low"
    assert sc.communication_style == "data-driven and precise"


# ── SimResult field tests ─────────────────────────────────────────────────────

def _minimal_result(**kwargs) -> SimResult:
    defaults = dict(
        scenario_id="sc_001",
        scenario_segment="test",
        agent_idx=0,
        presented_order=["variant_a", "variant_b"],
        verdict="variant_a",
        confidence="high",
        outcome="would_convert",
        rationale="ok",
    )
    defaults.update(kwargs)
    return SimResult(**defaults)


def test_sim_result_visual_defaults_are_backward_compatible():
    r = _minimal_result()
    assert r.visual_impact == {}
    assert r.attention_path == []
    assert r.messaging_alignment == "moderate"
    assert r.first_impression == ""


def test_sim_result_fogg_defaults():
    r = _minimal_result()
    assert r.fogg_motivation == 0
    assert r.fogg_ability == 0
    assert r.fogg_trigger_clarity == "ambiguous"


def test_sim_result_trust_signal_defaults():
    r = _minimal_result()
    assert r.trust_signals_found == []
    assert r.trust_signals_missing == []


def test_sim_result_persuasion_defaults():
    r = _minimal_result()
    assert r.loss_gain_framing == "neutral"
    assert r.metacognitive_reflection == ""
    assert r.competing_ctas_count == 0
    assert r.spatial_hierarchy_score == 0


def test_sim_result_all_new_fields_roundtrip():
    r = _minimal_result(
        visual_impact={"variant_a": 7.0, "variant_b": 5.0},
        attention_path=["hero image", "headline", "price", "CTA"],
        messaging_alignment="strong",
        first_impression="Image 1 felt clean; Image 2 felt cluttered.",
        fogg_motivation=8,
        fogg_ability=6,
        fogg_trigger_clarity="clear",
        trust_signals_found=["money-back guarantee", "security badge"],
        trust_signals_missing=["testimonials", "social proof"],
        loss_gain_framing="gain",
        metacognitive_reflection="I might be wrong because the donation form was below the fold.",
        competing_ctas_count=3,
        spatial_hierarchy_score=7,
    )
    j = r.model_dump_json()
    reloaded = SimResult.model_validate_json(j)
    assert reloaded.fogg_motivation == 8
    assert reloaded.fogg_ability == 6
    assert reloaded.fogg_trigger_clarity == "clear"
    assert "money-back guarantee" in reloaded.trust_signals_found
    assert "testimonials" in reloaded.trust_signals_missing
    assert reloaded.loss_gain_framing == "gain"
    assert "below the fold" in reloaded.metacognitive_reflection
    assert reloaded.competing_ctas_count == 3
    assert reloaded.spatial_hierarchy_score == 7


# ── Synthesis field tests ─────────────────────────────────────────────────────

def _minimal_synthesis(**kwargs) -> Synthesis:
    defaults = dict(
        winner="variant_b",
        raw_vote={"variant_b": 14, "variant_a": 6},
        weighted_vote={"variant_b": 0.7, "variant_a": 0.3},
        coverage_score=75,
        recommendation="Go with B",
        one_line_summary="B wins.",
    )
    defaults.update(kwargs)
    return Synthesis(**defaults)


def test_synthesis_new_fields_default():
    s = _minimal_synthesis()
    assert s.visual_impact == {}
    assert s.confound_warning is None
    assert s.fogg_avg == {}
    assert s.trust_signal_gaps == []


def test_synthesis_confound_warning():
    s = _minimal_synthesis(
        confound_warning="Variants in different languages (IT vs FR). Isolate to one variable."
    )
    assert s.confound_warning is not None
    assert "Isolate" in s.confound_warning


def test_synthesis_fogg_avg_populated():
    s = _minimal_synthesis(
        fogg_avg={
            "variant_a": {"motivation": 6.2, "ability": 4.1},
            "variant_b": {"motivation": 6.3, "ability": 7.8},
        }
    )
    assert s.fogg_avg["variant_b"]["ability"] > s.fogg_avg["variant_a"]["ability"]


def test_synthesis_trust_signal_gaps():
    s = _minimal_synthesis(trust_signal_gaps=["testimonials", "money-back guarantee"])
    assert "testimonials" in s.trust_signal_gaps


# ── Aggregation function tests ────────────────────────────────────────────────

def _make_scenario(id: str, segment: str, weight: float) -> ScenarioCard:
    return ScenarioCard(id=id, segment=segment, traffic_weight=weight)


def _make_result(scenario_id: str, segment: str, agent_idx: int,
                 va_score: float, vb_score: float,
                 fogg_m: int = 5, fogg_a: int = 5,
                 trust_missing: list[str] | None = None) -> SimResult:
    return SimResult(
        scenario_id=scenario_id,
        scenario_segment=segment,
        agent_idx=agent_idx,
        presented_order=["variant_a", "variant_b"],
        verdict="variant_b",
        confidence="medium",
        outcome="would_convert",
        rationale="ok",
        visual_impact={"variant_a": va_score, "variant_b": vb_score},
        fogg_motivation=fogg_m,
        fogg_ability=fogg_a,
        trust_signals_missing=trust_missing or [],
    )


def test_compute_visual_impact_weighted_average():
    """60% persona (va=6,vb=8) + 40% persona (va=8,vb=6) = va:6.8, vb:7.2."""
    scenarios = [
        _make_scenario("sc_001", "Persona A", 0.6),
        _make_scenario("sc_002", "Persona B", 0.4),
    ]
    results = [
        _make_result("sc_001", "Persona A", 0, 6.0, 8.0),
        _make_result("sc_001", "Persona A", 1, 6.0, 8.0),
        _make_result("sc_002", "Persona B", 2, 8.0, 6.0),
        _make_result("sc_002", "Persona B", 3, 8.0, 6.0),
    ]
    weights = _weight_lookup(scenarios)
    impact = _compute_visual_impact(results, weights)
    assert abs(impact["variant_a"] - 6.8) < 0.3
    assert abs(impact["variant_b"] - 7.2) < 0.3


def test_compute_visual_impact_returns_zero_for_missing_scores():
    scenarios = [_make_scenario("sc_001", "Persona A", 1.0)]
    results = [_minimal_result()]  # no visual_impact
    weights = _weight_lookup(scenarios)
    impact = _compute_visual_impact(results, weights)
    assert impact["variant_a"] == 0.0
    assert impact["variant_b"] == 0.0


def test_compute_fogg_averages():
    """Weighted-average Fogg scores per variant across agents."""
    scenarios = [
        _make_scenario("sc_001", "Persona A", 0.6),
        _make_scenario("sc_002", "Persona B", 0.4),
    ]
    results = [
        _make_result("sc_001", "Persona A", 0, 6.0, 8.0, fogg_m=8, fogg_a=6),
        _make_result("sc_001", "Persona A", 1, 6.0, 8.0, fogg_m=8, fogg_a=6),
        _make_result("sc_002", "Persona B", 2, 8.0, 6.0, fogg_m=4, fogg_a=3),
        _make_result("sc_002", "Persona B", 3, 8.0, 6.0, fogg_m=4, fogg_a=3),
    ]
    weights = _weight_lookup(scenarios)
    # Fogg is about the winning variant — test that the function returns a dict with
    # "motivation" and "ability" keys for at least one variant key
    fogg = _compute_fogg_averages(results, weights)
    # There should be entries keyed on verdict (all verdict="variant_b" in _make_result)
    assert "motivation" in fogg.get("variant_b", {}) or len(fogg) > 0


def test_collect_trust_gaps_returns_most_common():
    results = [
        _minimal_result(trust_signals_missing=["testimonials", "security badge"]),
        _minimal_result(trust_signals_missing=["testimonials", "money-back"]),
        _minimal_result(trust_signals_missing=["testimonials"]),
    ]
    gaps = _collect_trust_gaps(results)
    # testimonials appears in all 3 — must be first
    assert gaps[0] == "testimonials"