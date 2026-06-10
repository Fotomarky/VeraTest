"""Smoke tests for the describe-mode HTTP surface — POST /api/agent/run.

No Gemini key, no network, no google-adk: launch_from_description is mocked at
the module boundary, matching the import-guard pattern in test_agent.py. The
TestClient is used without the lifespan context so no DB/Phoenix init runs.
"""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from simab import agent_runtime
from simab import main as main_mod
from simab.config import CONFIG


@pytest.fixture()
def client():
    return TestClient(main_mod.app, raise_server_exceptions=False)


def _png(name: str = "shot.png"):
    return {"variant_a": (name, io.BytesIO(b"png-bytes"), "image/png")}


def _upload_files() -> set[str]:
    root = Path(CONFIG.upload_dir)
    return {p.name for p in root.glob("*")} if root.exists() else set()


# ---------------------------------------------------------------------------
# /api/agent/run — 400 / 503 / run_id / clarification branching
# ---------------------------------------------------------------------------

def test_run_empty_description_400(client):
    res = client.post("/api/agent/run", data={"description": "   "}, files=_png())
    assert res.status_code == 400


def test_run_missing_variant_a_422(client):
    # variant_a is a required UploadFile — FastAPI rejects the missing file.
    res = client.post("/api/agent/run", data={"description": "sell more shoes"})
    assert res.status_code == 422


def test_run_agent_unavailable_503_and_cleans_orphans(client, monkeypatch):
    async def _boom(description, a, b=None):
        raise RuntimeError("Describe mode is unavailable")
    monkeypatch.setattr(agent_runtime, "launch_from_description", _boom)

    before = _upload_files()
    res = client.post(
        "/api/agent/run", data={"description": "sell more shoes"}, files=_png()
    )
    assert res.status_code == 503
    assert "RuntimeError" in res.json()["detail"]
    # The just-saved upload must be deleted — no run was created to consume it.
    assert _upload_files() == before


def test_run_success_returns_run_id_and_keeps_upload(client, monkeypatch):
    async def _ok(description, a, b=None):
        assert b is None  # single-screen: variant_b absent -> None
        assert Path(a).exists()  # file must still be on disk for the pipeline
        return {"run_id": "run_test123"}
    monkeypatch.setattr(agent_runtime, "launch_from_description", _ok)

    before = _upload_files()
    res = client.post(
        "/api/agent/run", data={"description": "sell more shoes"}, files=_png()
    )
    assert res.status_code == 200
    body = res.json()
    assert body["run_id"] == "run_test123"
    assert body["dashboard_url"].endswith("/runs/run_test123")
    # On success the upload is kept (the pipeline reads it) — clean up after.
    new = _upload_files() - before
    assert len(new) == 1
    (Path(CONFIG.upload_dir) / new.pop()).unlink()


def test_run_clarification_passthrough_and_cleans_orphans(client, monkeypatch):
    async def _ask(description, a, b=None):
        return {"needs_clarification": True, "question": "What is the goal?"}
    monkeypatch.setattr(agent_runtime, "launch_from_description", _ask)

    before = _upload_files()
    res = client.post("/api/agent/run", data={"description": "hmm"}, files=_png())
    assert res.status_code == 200
    body = res.json()
    assert body["needs_clarification"] is True
    assert body["question"] == "What is the goal?"
    assert "dashboard_url" not in body
    # No run created -> uploads cleaned.
    assert _upload_files() == before


def test_run_ab_mode_passes_both_paths(client, monkeypatch):
    captured = {}

    async def _ok(description, a, b=None):
        captured["a"], captured["b"] = a, b
        return {"run_id": "run_ab"}
    monkeypatch.setattr(agent_runtime, "launch_from_description", _ok)

    res = client.post(
        "/api/agent/run",
        data={"description": "compare these"},
        files={
            "variant_a": ("a.png", io.BytesIO(b"a"), "image/png"),
            "variant_b": ("b.png", io.BytesIO(b"b"), "image/png"),
        },
    )
    assert res.status_code == 200
    assert captured["b"] is not None and Path(captured["b"]).exists()
    # Clean up both saved files.
    for p in (captured["a"], captured["b"]):
        Path(p).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Filename sanitization stays inside upload_dir
# ---------------------------------------------------------------------------

def test_run_sanitizes_traversal_filename(client, monkeypatch):
    captured = {}

    async def _ok(description, a, b=None):
        captured["a"] = a
        return {"run_id": "run_trav"}
    monkeypatch.setattr(agent_runtime, "launch_from_description", _ok)

    res = client.post(
        "/api/agent/run",
        data={"description": "go"},
        files={"variant_a": ("x/../../../etc/evil.png", io.BytesIO(b"png"), "image/png")},
    )
    assert res.status_code == 200
    a_path = Path(captured["a"])
    upload_root = Path(CONFIG.upload_dir).resolve()
    assert a_path.resolve().is_relative_to(upload_root)
    assert a_path.name.endswith("_a_evil.png")
    a_path.unlink(missing_ok=True)


def test_safe_upload_name_edge_cases():
    f = main_mod._safe_upload_name
    assert f("shot.png") == "shot.png"
    assert f("x/../../../etc/evil.png") == "evil.png"
    assert f("..") == "upload.png"   # Path("..").name is ".." -> explicit reject
    assert f("") == "upload.png"
    assert f(None) == "upload.png"
