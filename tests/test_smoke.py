"""Smoke tests — don't require a real Gemini API key.

Covers: schemas validate, state writes/reads, allocator math, distributed mutex.
"""
import pytest

from simab import state
from simab.agents.scenarios import _allocate
from simab.models import (
    AuditReport, Brief, FrictionTheme, ScenarioCard, SimResult, Synthesis,
)


@pytest.mark.asyncio
async def test_create_and_get_run():
    run_id = await state.create_run(
        goal="sign up",
        audience_raw="",
        persona_source="paste",
        variant_a_path="/tmp/a.png",
        variant_b_path="/tmp/b.png",
    )
    assert run_id.startswith("run_")
    run = await state.get_run(run_id)
    assert run is not None
    assert run.status == "pending"
    assert run.goal == "sign up"


@pytest.mark.asyncio
async def test_status_updates():
    run_id = await state.create_run(
        goal="test", audience_raw="", persona_source="paste",
        variant_a_path="/x", variant_b_path="/y",
    )
    await state.set_status(run_id, "simulating")
    run = await state.get_run(run_id)
    assert run.status == "simulating"


@pytest.mark.asyncio
async def test_brief_round_trip():
    run_id = await state.create_run(
        goal="g", audience_raw="", persona_source="paste",
        variant_a_path="/a", variant_b_path="/b",
    )
    brief = Brief(
        conversion_goal="g",
        variant_a_summary="A is simple",
        variant_b_summary="B has more info",
        key_differences=["copy", "CTA"],
        inferred_personas=[
            ScenarioCard(id="sc_001", segment="evaluator", traffic_weight=0.6),
            ScenarioCard(id="sc_002", segment="impulse", traffic_weight=0.4),
        ],
    )
    await state.write_brief(run_id, brief)
    run = await state.get_run(run_id)
    assert run.brief is not None
    assert len(run.brief.inferred_personas) == 2
    assert run.brief.inferred_personas[0].segment == "evaluator"


@pytest.mark.asyncio
async def test_sim_result_idempotent_mutex():
    """The mutex pattern: writing same (run_id, scenario_id, agent_idx) twice
    succeeds once, fails-silently the second time."""
    run_id = await state.create_run(
        goal="g", audience_raw="", persona_source="paste",
        variant_a_path="/a", variant_b_path="/b",
    )
    result = SimResult(
        scenario_id="sc_001",
        scenario_segment="test",
        agent_idx=0,
        cohort="variant_a",
        resonance={"motivation": 7, "identity": 6, "situation": 5, "beliefs": 6, "ability": 7, "trigger": 6},
        resonance_overall=6.3,
        intent_signal="would_research",
        confidence="high",
        rationale="ok",
    )
    written1 = await state.append_sim_result(run_id, result)
    written2 = await state.append_sim_result(run_id, result)  # duplicate
    assert written1 is True
    assert written2 is False  # mutex prevents duplicate
    count = await state.count_sim_results(run_id)
    assert count == 1


@pytest.mark.asyncio
async def test_different_agent_idx_both_succeed():
    """Same scenario_id with DIFFERENT agent_idx should both write."""
    run_id = await state.create_run(
        goal="g", audience_raw="", persona_source="paste",
        variant_a_path="/a", variant_b_path="/b",
    )
    r1 = SimResult(scenario_id="sc_001", scenario_segment="t", agent_idx=0,
                   cohort="variant_a", resonance={"motivation":6,"identity":6,"situation":6,"beliefs":6,"ability":6,"trigger":6},
                   resonance_overall=6.0, intent_signal="would_research",
                   confidence="high", rationale="")
    r2 = SimResult(scenario_id="sc_001", scenario_segment="t", agent_idx=1,
                   cohort="variant_b", resonance={"motivation":7,"identity":7,"situation":7,"beliefs":7,"ability":7,"trigger":7},
                   resonance_overall=7.0, intent_signal="would_act",
                   confidence="high", rationale="")
    assert await state.append_sim_result(run_id, r1) is True
    assert await state.append_sim_result(run_id, r2) is True
    assert await state.count_sim_results(run_id) == 2


def test_allocator_proportional():
    """60/20/20 weights with 20 agents → 12/4/4."""
    weights = [0.6, 0.2, 0.2]
    counts = _allocate(weights, 20)
    assert sum(counts) == 20
    assert counts[0] >= 11 and counts[0] <= 13  # 12 ± rounding
    assert counts[1] >= 3 and counts[1] <= 5
    assert counts[2] >= 3 and counts[2] <= 5


def test_allocator_equal_split():
    """Equal weights → even distribution."""
    counts = _allocate([1, 1, 1, 1], 20)
    assert sum(counts) == 20
    assert max(counts) - min(counts) <= 1


def test_allocator_zero_weights_falls_back():
    counts = _allocate([0, 0, 0], 20)
    assert sum(counts) == 20


def test_scenario_card_validates():
    sc = ScenarioCard(id="sc_001", segment="test", traffic_weight=0.5)
    assert sc.intent == "evaluate"
    assert sc.device == "desktop"
    assert sc.locale == "en-US"
    assert sc.visual_style_preference == ""
    assert sc.patience_threshold == "medium"
    assert sc.communication_style == ""


def test_brief_serializes():
    brief = Brief(
        conversion_goal="g",
        variant_a_summary="a",
        variant_b_summary="b",
        key_differences=["x"],
    )
    j = brief.model_dump_json()
    assert "conversion_goal" in j
    reloaded = Brief.model_validate_json(j)
    assert reloaded.conversion_goal == "g"


@pytest.mark.asyncio
async def test_persona_library_save_and_list():
    sc = ScenarioCard(id="sc_persona_1", segment="evaluator", traffic_weight=0.5)
    await state.save_persona(sc, tags=["saas", "b2b"])
    personas = await state.list_personas()
    assert any(p.id == "sc_persona_1" for p in personas)
    tagged = await state.list_personas(tag="saas")
    assert any(p.id == "sc_persona_1" for p in tagged)


# ---------------------------------------------------------------------------
# Task 2 — calibration layer model additions
# ---------------------------------------------------------------------------

def test_fidelity_report_model_roundtrips():
    from simab.models import FidelityReport

    fr = FidelityReport(
        persona_consistency=0.95,
        agents_drifted=1,
        rationale_coherence=0.90,
        agents_incoherent=2,
        eval_explanations=["agent_3 used 'as an AI' phrasing"],
        drifted_agent_indices=[3],
    )
    assert fr.persona_consistency == 0.95
    reloaded = FidelityReport.model_validate_json(fr.model_dump_json())
    assert reloaded.agents_drifted == 1
    assert reloaded.drifted_agent_indices == [3]


def test_simresult_has_optional_span_id():
    sr = SimResult(
        scenario_id="sc_1", scenario_segment="x",
        agent_idx=0, cohort="variant_a",
    )
    assert sr.span_id is None
    sr2 = sr.model_copy(update={"span_id": "abc123"})
    assert sr2.span_id == "abc123"


def test_run_has_optional_fidelity_slice():
    from simab.models import Run
    run = Run(run_id="r1", goal="g", variant_a_path="/x.png")
    assert run.fidelity is None


def test_run_status_includes_narrating_and_calibrating():
    # Pydantic Literal values — round-trip via model_validate on the Run model.
    from simab.models import Run
    for status in ("narrating", "calibrating"):
        run = Run(run_id=f"r_{status}", goal="g",
                  variant_a_path="/x.png", status=status)
        assert run.status == status


@pytest.mark.asyncio
async def test_write_fidelity_persists_slice(tmp_path, monkeypatch):
    """write_fidelity round-trips through SQLite."""
    monkeypatch.setenv("SIMAB_DB_PATH", str(tmp_path / "test.db"))
    # Reload CONFIG so the new db_path is picked up.
    import importlib
    from simab import config as _config_mod
    importlib.reload(_config_mod)
    from simab import state as _state_mod
    importlib.reload(_state_mod)
    from simab.models import FidelityReport

    rid = await _state_mod.create_run(
        goal="g", audience_raw="a", persona_source="paste",
        variant_a_path="/x.png", variant_b_path=None,
    )
    fr = FidelityReport(
        persona_consistency=0.95, agents_drifted=1,
        rationale_coherence=0.9, agents_incoherent=2,
    )
    await _state_mod.write_fidelity(rid, fr)

    run = await _state_mod.get_run(rid)
    assert run is not None
    assert run.fidelity is not None
    assert run.fidelity.persona_consistency == 0.95
    assert run.fidelity.agents_drifted == 1
    assert run.fidelity.agents_incoherent == 2
    await _state_mod.close_db()
