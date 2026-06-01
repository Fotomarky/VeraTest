"""Smoke tests for the FidelityAuditor (Phase 7).

Mocks the Phoenix evals + client surface so the test doesn't require
arize-phoenix-evals or a live Phoenix instance. Validates the agent's
contract: it reads sim results, runs both evals (LLM + code), writes the
fidelity slice, and finalises the run to status=complete.
"""
from __future__ import annotations
import importlib
from unittest.mock import patch

import pandas as pd
import pytest


@pytest.mark.asyncio
async def test_fidelity_computes_persona_consistency_and_coherence(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SIMAB_DB_PATH", str(tmp_path / "test.db"))
    # Reload config + state so tmp_path takes effect.
    from simab import config as _config_mod
    importlib.reload(_config_mod)
    from simab import state as _state_mod
    importlib.reload(_state_mod)
    from simab.agents import fidelity as _fidelity_mod
    importlib.reload(_fidelity_mod)
    from simab.models import Brief, ScenarioCard, SimResult

    rid = await _state_mod.create_run(
        goal="g", audience_raw="b2b", persona_source="paste",
        variant_a_path="/a.png", variant_b_path=None,
    )
    await _state_mod.write_brief(rid, Brief(
        conversion_goal="g", variant_a_summary="x",
        inferred_personas=[],
    ))
    sc = ScenarioCard(id="sc_1", segment="impulse_buyer")
    await _state_mod.write_scenarios(rid, [sc], allocations=[])

    # Agent 0 — coherent: low score with negative rationale.
    await _state_mod.append_sim_result(rid, SimResult(
        scenario_id="sc_1", scenario_segment="impulse_buyer",
        agent_idx=0, cohort="variant_a",
        resonance={"motivation": 3, "identity": 4, "situation": 3,
                   "beliefs": 3, "ability": 4, "trigger": 3},
        resonance_overall=3.3,
        metacognitive_reflection="I felt confused and frustrated by the dense copy.",
    ))
    # Agent 1 — incoherent: HIGH score paired with negative rationale + "as an AI".
    await _state_mod.append_sim_result(rid, SimResult(
        scenario_id="sc_1", scenario_segment="impulse_buyer",
        agent_idx=1, cohort="variant_a",
        resonance={"motivation": 9, "identity": 9, "situation": 9,
                   "beliefs": 9, "ability": 9, "trigger": 9},
        resonance_overall=9.0,
        metacognitive_reflection=(
            "As an AI, I notice this page is confusing and frustrating; "
            "the user would find it overwhelming."
        ),
    ))

    fake_results = pd.DataFrame([
        {"label": "in_character", "explanation": "stayed in voice"},
        {"label": "drifted",      "explanation": "used 'as an AI' phrasing"},
    ])
    with patch("simab.agents.fidelity.llm_classify",
               return_value=fake_results) as mock_classify, \
         patch("simab.agents.fidelity._gemini_model",
               return_value=None) as _mock_model, \
         patch("simab.agents.fidelity.log_span_evaluations") as mock_log, \
         patch("simab.agents.fidelity.append_drifted_agents") as mock_append:
        await _fidelity_mod.run(rid)

    mock_classify.assert_called_once()
    assert mock_log.call_count >= 1  # at least persona_consistency + coherence
    mock_append.assert_called_once()

    run = await _state_mod.get_run(rid)
    assert run is not None
    assert run.fidelity is not None
    assert run.fidelity.persona_consistency == 0.5  # 1 of 2 in-character
    assert run.fidelity.agents_drifted == 1
    # Code-based coherence: agent 1 is incoherent (high score, negative rationale).
    assert run.fidelity.agents_incoherent >= 1
    assert 1 in run.fidelity.drifted_agent_indices
    assert run.status == "complete"

    await _state_mod.close_db()


@pytest.mark.asyncio
async def test_fidelity_skips_gracefully_with_no_sim_results(tmp_path,
                                                             monkeypatch):
    """Empty sim_results -> set status=complete, don't try to eval nothing."""
    monkeypatch.setenv("SIMAB_DB_PATH", str(tmp_path / "test.db"))
    from simab import config as _config_mod
    importlib.reload(_config_mod)
    from simab import state as _state_mod
    importlib.reload(_state_mod)
    from simab.agents import fidelity as _fidelity_mod
    importlib.reload(_fidelity_mod)

    rid = await _state_mod.create_run(
        goal="g", audience_raw="", persona_source="paste",
        variant_a_path="/a.png", variant_b_path=None,
    )
    await _fidelity_mod.run(rid)
    run = await _state_mod.get_run(rid)
    assert run is not None
    assert run.status == "complete"
    assert run.fidelity is None  # no slice written when no data

    await _state_mod.close_db()
