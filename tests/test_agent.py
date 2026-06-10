"""Smoke tests for the Agent Builder (ADK) layer — simab/agent.py.

These run WITHOUT a real Gemini key, without network, and without google-adk
installed (the module is import-guarded). The two agent tools are thin wrappers
over the existing pipeline/state, so we exercise them directly; the live
ADK Runner + Phoenix MCP path is validated manually (see docs/agent-builder.md).
"""
import pytest

from simab import agent, state


def test_agent_module_imports():
    """The module imports even when google-adk is absent (import guard)."""
    assert hasattr(agent, "start_pretest")
    assert hasattr(agent, "get_pretest_result")
    assert hasattr(agent, "build_root_agent")
    assert hasattr(agent, "_build_phoenix_toolset")


@pytest.mark.asyncio
async def test_agent_runtime_unavailable_without_adk(monkeypatch):
    """launch_from_description raises a clean RuntimeError (-> 503) when the
    agent isn't built, regardless of whether google-adk is installed. The
    /api/agent/launch endpoint maps this to a 503 so describe-mode degrades
    gracefully instead of 500-ing."""
    from simab import agent as agent_mod
    from simab import agent_runtime

    monkeypatch.setattr(agent_mod, "root_agent", None)
    monkeypatch.setattr(agent_runtime, "_runner", None)
    with pytest.raises(RuntimeError):
        await agent_runtime.launch_from_description("test", "/tmp/a.png")


@pytest.mark.asyncio
async def test_get_pretest_result_missing():
    out = await agent.get_pretest_result("does-not-exist")
    assert out["error"].startswith("run does-not-exist")


@pytest.mark.asyncio
async def test_get_pretest_result_after_create():
    run_id = await state.create_run(
        goal="sign up", audience_raw="", persona_source="paste",
        variant_a_path="/tmp/a.png", variant_b_path=None,
    )
    out = await agent.get_pretest_result(run_id)
    assert out["run_id"] == run_id
    assert "status" in out


@pytest.mark.asyncio
async def test_start_pretest_single_screen(monkeypatch):
    # Don't actually launch the 20-agent pipeline (it would call Gemini).
    async def _noop(run_id):
        return None
    monkeypatch.setattr(agent, "run_pipeline", _noop)

    out = await agent.start_pretest(
        goal="sign up", audience="founders", variant_a_path="/tmp/a.png",
    )
    import asyncio
    await asyncio.sleep(0)  # let the fire-and-forget task drain

    assert out["status"] == "started"
    assert out["mode"] == "single_screen"
    assert out["run_id"].startswith("run_")
    assert out["dashboard_url"].endswith(out["run_id"])
    # The run was really created in state.
    assert await state.get_run(out["run_id"]) is not None


@pytest.mark.asyncio
async def test_start_pretest_ab_mode(monkeypatch):
    async def _noop(run_id):
        return None
    monkeypatch.setattr(agent, "run_pipeline", _noop)

    out = await agent.start_pretest(
        goal="sign up", audience="founders",
        variant_a_path="/tmp/a.png", variant_b_path="/tmp/b.png",
    )
    import asyncio
    await asyncio.sleep(0)
    assert out["mode"] == "ab"


def test_build_root_agent_has_all_tools():
    """When google-adk is installed, the agent wires all three tools:
    start_pretest, get_pretest_result, and the Arize Phoenix MCP toolset.
    Skipped automatically in environments without the [agent] extra."""
    pytest.importorskip("google.adk")
    root = agent.build_root_agent()
    assert root.name == "veratest_concierge"
    names = [getattr(t, "__name__", type(t).__name__) for t in root.tools]
    assert "start_pretest" in names
    assert "get_pretest_result" in names
    # The Phoenix MCP toolset is the third tool (object, not a function).
    assert any("Toolset" in type(t).__name__ for t in root.tools)
