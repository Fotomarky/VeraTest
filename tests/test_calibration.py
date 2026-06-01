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
