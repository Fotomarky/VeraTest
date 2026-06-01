"""Smoke tests for the Phoenix client helper — no live Phoenix needed.

Validates that the helpers degrade safely to no-op when the Phoenix
dependency isn't installed or no API key / endpoint is configured. The
real Phoenix integration is verified manually via the end-to-end run with
PHOENIX_API_KEY set (Task 16).
"""
from __future__ import annotations
import pytest


def test_drift_history_returns_empty_when_disabled(monkeypatch):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    # Reload config + client to pick up the cleared env.
    import importlib
    from simab import config as _config_mod
    importlib.reload(_config_mod)
    from simab.integrations import phoenix_client
    importlib.reload(phoenix_client)
    phoenix_client._reset_client_for_test()

    history = phoenix_client.get_persona_drift_history(
        audience_signature="b2b_devtools",
    )
    assert history == {}


def test_append_drifted_agents_is_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    import importlib
    from simab import config as _config_mod
    importlib.reload(_config_mod)
    from simab.integrations import phoenix_client
    importlib.reload(phoenix_client)
    phoenix_client._reset_client_for_test()

    # Must not raise even with non-empty rows.
    phoenix_client.append_drifted_agents(
        run_id="r1",
        audience_signature="b2b_devtools",
        rows=[{"persona": "x", "rationale": "y"}],
    )


def test_audience_signature_is_stable():
    from simab.integrations.phoenix_client import audience_signature
    s1 = audience_signature("Startup founders evaluating CI tools")
    s2 = audience_signature("startup founders evaluating ci tools")
    s3 = audience_signature("Different audience")
    assert s1 == s2  # case-insensitive
    assert s1 != s3  # different audiences hash differently
    assert len(s1) <= 64


def test_inject_drift_constraints_strengthens_high_drift_personas():
    from simab.agents.scenarios import _inject_drift_constraints
    from simab.models import ScenarioCard

    cards = [
        ScenarioCard(id="sc_1", segment="impulse_buyer", decision_style="impulse",
                     constraints=["existing constraint"]),
        ScenarioCard(id="sc_2", segment="analyst", decision_style="analytical"),
    ]
    history = {"impulse_buyer": 0.40, "analyst": 0.05}
    out = _inject_drift_constraints(cards, history, threshold=0.25)
    impulse = next(c for c in out if c.segment == "impulse_buyer")
    analyst = next(c for c in out if c.segment == "analyst")
    assert any("STAY IN CHARACTER" in c for c in impulse.constraints), \
        f"impulse_buyer should get anti-drift constraint; got: {impulse.constraints}"
    # Existing constraints preserved (prepended-to, not replaced).
    assert "existing constraint" in impulse.constraints
    assert not any("STAY IN CHARACTER" in c for c in analyst.constraints)


def test_inject_stress_test_persona_always_added():
    from simab.agents.scenarios import _inject_stress_test_persona
    from simab.models import ScenarioCard

    cards = [ScenarioCard(id="sc_1", segment="impulse_buyer", traffic_weight=1.0)]
    out = _inject_stress_test_persona(cards)
    stress = [c for c in out if c.segment.startswith("stress_test")]
    assert len(stress) == 1, f"expected exactly one stress-test card, got {len(out)}"
    # Weights sum to ~1.0 after rescaling.
    assert abs(sum(c.traffic_weight for c in out) - 1.0) < 1e-6


def test_inject_stress_test_persona_handles_empty():
    from simab.agents.scenarios import _inject_stress_test_persona
    out = _inject_stress_test_persona([])
    assert len(out) == 1
    assert out[0].segment.startswith("stress_test")
    assert out[0].traffic_weight == 1.0
