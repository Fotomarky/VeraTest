# Arize Track — Calibration Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three Arize-track gaps (Phoenix MCP introspection, self-improvement loop, LLM-as-a-Judge evals) by adding a Calibration Layer that measures every run's persona-fidelity, persists it across runs in Phoenix, and feeds it back into the next run's ScenarioBuilder.

**Architecture:** New Phase 7 `FidelityAuditor` (LLM-as-a-Judge + code-based eval, writes Phoenix Span Evaluations + appends drift cases to a Phoenix Dataset). `ScenarioBuilder` queries Phoenix for historical persona-drift rates and tightens prompts when drift > 25%. Every run wraps its 24 spans inside a single Phoenix Session for visual clarity. Phoenix MCP server is configured for runtime introspection from MCP clients (Claude Desktop / Gemini CLI / Cursor). The base FastAPI + stigmergy architecture is unchanged — Phoenix becomes the *cross-run* substrate alongside SQLite's *within-run* substrate.

**Tech Stack:** Python 3.11 · FastAPI · aiosqlite · `arize-phoenix-evals` (LLM-as-a-Judge) · `arize-phoenix-client` (datasets/experiments) · `openinference-instrumentation-google-genai` (already wired in `simab/integrations/phoenix.py`) · `@arizeai/phoenix-mcp` (npm, Phoenix MCP server) · OpenTelemetry sessions API.

---

## File map

**New files:**

- `simab/agents/fidelity.py` — Phase 7 FidelityAuditor (LLM-as-a-Judge + code-based eval + Phoenix writes)
- `simab/integrations/phoenix_client.py` — thin Phoenix Python client helpers (history query, dataset append, experiments)
- `simab/integrations/session.py` — OpenTelemetry session context manager for `run_pipeline`
- `tests/test_fidelity.py` — smoke tests for Phase 7 with mocked Phoenix
- `tests/test_calibration.py` — smoke tests for the history-query → prompt-tightening loop
- `scripts/run_calibration_experiment.py` — standalone script that runs the Phoenix Experiment (baseline vs tightened) for the demo video
- `mcp/phoenix-mcp.example.json` — example Phoenix MCP server config to drop into Claude Desktop / Gemini CLI / Cursor

**Modified files:**

- `simab/models.py` — add `SimResult.span_id`, `FidelityReport`, `Run.fidelity`, `RunStatus` adds `"calibrating"`
- `simab/state.py` — add `fidelity_json` column, `write_fidelity()` setter, include in `get_run()` projection
- `simab/config.py` — add `phoenix_api_key`, `phoenix_project`, `fidelity_drift_threshold` fields
- `simab/pipeline.py` — wrap in session; add Phase 7 call between `narrative` and `complete`
- `simab/agents/simulator.py` — wrap `generate()` in a per-agent span; capture span_id and persist on `SimResult`
- `simab/agents/scenarios.py` — read persona-drift history via `phoenix_client`, inject anti-drift constraint when drift > threshold; always inject one stress-test persona
- `simab/main.py` — call `init_phoenix()` at FastAPI startup (currently dead code!)
- `simab/exports.py` — include fidelity in the markdown / PM summary exports
- `frontend/app/runs/[id]/page.tsx` — pass `fidelity` to `CommandRail`
- `frontend/app/runs/[id]/components/CommandRail.tsx` — render fidelity badge ("19/20 in character · 95%")
- `pyproject.toml` — add `arize-phoenix-evals` and `arize-phoenix-client` to the `phoenix` extra
- `README.md` — fidelity badge story · no-framework defense paragraph · Phoenix MCP setup · drop competing-platform refs
- `CLAUDE.md` — add Phase 7 to the agent slice table and pipeline diagram

---

## Task 1 — Dependencies and config

**Files:**
- Modify: `pyproject.toml:28`
- Modify: `simab/config.py:1-40`

- [ ] **Step 1: Add Phoenix evals + client to the phoenix extra**

Modify `pyproject.toml`. Replace the line:

```toml
phoenix = ["arize-phoenix>=4.0", "arize-phoenix-otel>=0.5", "openinference-instrumentation>=0.1"]
```

with:

```toml
phoenix = [
    "arize-phoenix>=4.0",
    "arize-phoenix-otel>=0.5",
    "arize-phoenix-evals>=0.13",
    "arize-phoenix-client>=1.0",
    "openinference-instrumentation>=0.1",
    "openinference-instrumentation-google-genai>=0.1",
]
```

- [ ] **Step 2: Install in the existing venv**

```bash
source .venv/bin/activate
uv pip install -e ".[dev,phoenix]"
```

Expected: installs cleanly (no version conflicts).

- [ ] **Step 3: Extend `CONFIG` with three new fields**

Read `simab/config.py`. Add three fields to the frozen dataclass and `from_env()`:

```python
phoenix_api_key: str | None
phoenix_project: str
fidelity_drift_threshold: float
```

In `from_env()`:

```python
phoenix_api_key=os.environ.get("PHOENIX_API_KEY") or None,
phoenix_project=os.environ.get("PHOENIX_PROJECT", "veratest"),
fidelity_drift_threshold=float(os.environ.get("VERATEST_DRIFT_THRESHOLD", "0.25")),
```

- [ ] **Step 4: Smoke test the config loads**

```bash
pytest tests/test_smoke.py -k config -v
```

Expected: PASS (the existing `test_config_from_env` covers this).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml simab/config.py
git commit -m "feat(arize): add phoenix evals + client deps and calibration config"
```

---

## Task 2 — New model fields (SimResult.span_id, FidelityReport, Run.fidelity)

**Files:**
- Modify: `simab/models.py:113-160` (SimResult), `:225-262` (Run + RunStatus)
- Test: `tests/test_smoke.py` (add one test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_smoke.py`:

```python
def test_fidelity_report_model_roundtrips():
    from simab.models import FidelityReport, Run, SimResult

    fr = FidelityReport(
        persona_consistency=0.95,
        agents_drifted=1,
        rationale_coherence=0.90,
        agents_incoherent=2,
        eval_explanations=["agent_3 used 'as an AI' phrasing"],
    )
    assert fr.persona_consistency == 0.95
    # round-trip
    assert FidelityReport.model_validate_json(fr.model_dump_json()).agents_drifted == 1

def test_simresult_has_optional_span_id():
    from simab.models import SimResult
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
```

- [ ] **Step 2: Run the test — it must fail with AttributeError**

```bash
pytest tests/test_smoke.py::test_fidelity_report_model_roundtrips tests/test_smoke.py::test_simresult_has_optional_span_id tests/test_smoke.py::test_run_has_optional_fidelity_slice -v
```

Expected: 3 FAIL (model fields don't exist yet).

- [ ] **Step 3: Add `span_id` to SimResult**

In `simab/models.py`, in the `SimResult` class (around line 113), add:

```python
span_id: Optional[str] = None  # Phoenix span id captured at trace time
```

- [ ] **Step 4: Add `FidelityReport` model and `Run.fidelity`**

Above the `Run` class in `simab/models.py`, add:

```python
class FidelityReport(BaseModel):
    """Phase 7 output: how faithfully agents simulated their personas."""
    persona_consistency: float = Field(ge=0.0, le=1.0)
    """Fraction of agents that stayed in-character (LLM-as-a-Judge)."""
    agents_drifted: int = 0
    rationale_coherence: float = Field(default=1.0, ge=0.0, le=1.0)
    """Fraction of agents whose numeric score aligned with rationale tone (code eval)."""
    agents_incoherent: int = 0
    eval_explanations: list[str] = Field(default_factory=list)
    drifted_agent_indices: list[int] = Field(default_factory=list)
```

In the `Run` class, add `fidelity` slice after `synthesis`:

```python
fidelity: Optional[FidelityReport] = None
```

Extend `RunStatus` Literal to include `"calibrating"`:

```python
RunStatus = Literal[
    "pending",
    "normalizing",
    "building_scenarios",
    "simulating",
    "auditing",
    "synthesizing",
    "calibrating",      # new — Phase 7 FidelityAuditor
    "complete",
    "failed",
]
```

- [ ] **Step 5: Run tests — they should now pass**

```bash
pytest tests/test_smoke.py -v
```

Expected: all 31+ PASS including the 3 new ones.

- [ ] **Step 6: Commit**

```bash
git add simab/models.py tests/test_smoke.py
git commit -m "feat(models): add SimResult.span_id, FidelityReport, Run.fidelity slice"
```

---

## Task 3 — Persist the fidelity slice in SQLite

**Files:**
- Modify: `simab/state.py` (SCHEMA + `get_run()` + new `write_fidelity()`)
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_smoke.py`:

```python
async def test_write_fidelity_persists_slice(tmp_path, monkeypatch):
    from simab import state
    from simab.models import FidelityReport
    monkeypatch.setenv("SIMAB_DB_PATH", str(tmp_path / "test.db"))
    from simab.config import CONFIG  # noqa — reload not needed; state reads fresh
    state._db = None  # force reconnect to the tmp path

    rid = await state.create_run(
        goal="g", audience_raw="a", persona_source="paste",
        variant_a_path="/x.png", variant_b_path=None,
    )
    fr = FidelityReport(persona_consistency=0.95, agents_drifted=1)
    await state.write_fidelity(rid, fr)

    run = await state.get_run(rid)
    assert run is not None
    assert run.fidelity is not None
    assert run.fidelity.persona_consistency == 0.95
    assert run.fidelity.agents_drifted == 1
    await state.close_db()
```

- [ ] **Step 2: Run the test — expect FAIL (no `write_fidelity`, no column)**

```bash
pytest tests/test_smoke.py::test_write_fidelity_persists_slice -v
```

Expected: FAIL with AttributeError or OperationalError.

- [ ] **Step 3: Add the column to SCHEMA**

In `simab/state.py`, inside the `SCHEMA` string, add `fidelity_json TEXT,` after `synthesis_json TEXT,`:

```python
synthesis_json TEXT,
fidelity_json TEXT,
error TEXT
```

- [ ] **Step 4: Add a migration call for existing databases**

After the `executescript(SCHEMA)` line in `get_db()`:

```python
# Idempotent migration for fidelity_json on pre-existing DBs.
try:
    await _db.execute("ALTER TABLE runs ADD COLUMN fidelity_json TEXT")
    await _db.commit()
except aiosqlite.OperationalError:
    pass  # column already exists
```

- [ ] **Step 5: Read the column in `get_run()`**

Add `FidelityReport` to the imports in `simab/state.py`:

```python
from .models import (
    AudiencePreset, Run, Brief, ScenarioCard, SimResult, AuditReport,
    Synthesis, FidelityReport, RunStatus,
)
```

In `get_run()`, before the `return Run(...)`, add:

```python
fidelity_json = data.get("fidelity_json")
```

And in the `Run(...)` construction, add the field:

```python
fidelity=FidelityReport.model_validate_json(fidelity_json) if fidelity_json else None,
```

- [ ] **Step 6: Add the `write_fidelity()` setter**

After the existing `write_synthesis` (or near the bottom of the writes section) in `simab/state.py`:

```python
async def write_fidelity(run_id: str, fidelity: FidelityReport) -> None:
    db = await get_db()
    await db.execute(
        """UPDATE runs SET fidelity_json=?,
           phases_complete=json_insert(phases_complete, '$[#]', ?),
           updated_at=? WHERE run_id=?""",
        (fidelity.model_dump_json(), "fidelity",
         datetime.now(timezone.utc).isoformat(), run_id),
    )
    await db.commit()
```

- [ ] **Step 7: Run the new test + the full smoke suite**

```bash
pytest tests/test_smoke.py -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add simab/state.py tests/test_smoke.py
git commit -m "feat(state): persist fidelity slice in SQLite with idempotent migration"
```

---

## Task 4 — Wire `init_phoenix()` into FastAPI startup

**Files:**
- Modify: `simab/main.py` (find the FastAPI app + startup hook)
- Modify: `simab/integrations/phoenix.py` (already exists — verify project name reads CONFIG)

- [ ] **Step 1: Update `init_phoenix()` to use the configured project name**

Read `simab/integrations/phoenix.py`. Replace the hardcoded `project_name="simab"` with:

```python
tracer_provider = register(
    project_name=CONFIG.phoenix_project,
    endpoint=CONFIG.phoenix_endpoint,
    auto_instrument=False,
    headers={"api_key": CONFIG.phoenix_api_key} if CONFIG.phoenix_api_key else None,
)
```

- [ ] **Step 2: Find the FastAPI app object in main.py**

```bash
grep -nE "FastAPI\(|app = " simab/main.py | head -5
```

Note the line where `app = FastAPI(...)` is defined.

- [ ] **Step 3: Add the startup hook**

In `simab/main.py`, immediately after the `app = FastAPI(...)` line, add:

```python
from .integrations.phoenix import init_phoenix

@app.on_event("startup")
async def _startup_phoenix() -> None:
    init_phoenix()
```

(If `main.py` already uses `lifespan=` instead of decorators, fold the `init_phoenix()` call into the existing lifespan context manager instead.)

- [ ] **Step 4: Verify the server boots without Phoenix configured**

```bash
unset PHOENIX_COLLECTOR_ENDPOINT
uvicorn simab.main:app --port 8001 &
sleep 2
curl -s http://localhost:8001/health
kill %1
```

Expected: `{"status":"ok",...}` and a log line `Phoenix not configured ... — skipping`.

- [ ] **Step 5: Commit**

```bash
git add simab/main.py simab/integrations/phoenix.py
git commit -m "feat(observability): wire Phoenix tracer init at FastAPI startup"
```

---

## Task 5 — Wrap each run in a Phoenix Session (Refinement 3)

**Files:**
- Create: `simab/integrations/session.py`
- Modify: `simab/pipeline.py:44-62` (run_pipeline)

- [ ] **Step 1: Create the session context manager**

Create `simab/integrations/session.py`:

```python
"""OpenTelemetry session wrapper for a single pipeline run.

Phoenix surfaces sessions in its UI as a single grouping of all spans for
one logical workflow — i.e. all ~24 Gemini calls of one VeraTest run.
"""
from __future__ import annotations
import contextlib
import logging

log = logging.getLogger(__name__)


@contextlib.contextmanager
def run_session(run_id: str):
    """Context manager that wraps a pipeline run in one Phoenix session span."""
    try:
        from opentelemetry import trace
    except ImportError:
        log.debug("opentelemetry not installed — session span skipped")
        yield
        return

    tracer = trace.get_tracer("simab.pipeline")
    with tracer.start_as_current_span(
        name=f"veratest_run.{run_id}",
        attributes={
            "openinference.session.id": run_id,
            "veratest.run_id": run_id,
        },
    ):
        yield
```

- [ ] **Step 2: Use it in `run_pipeline`**

In `simab/pipeline.py`, modify `run_pipeline` to wrap the phase calls:

```python
from .integrations.session import run_session

async def run_pipeline(run_id: str) -> None:
    log.info(f"[{run_id}] pipeline start")
    try:
        with run_session(run_id):
            await normalizer.run(run_id)
            await scenarios.run(run_id)
            await _run_simulators(run_id)
            await auditor.run(run_id)
            await synthesizer.run(run_id)
            await narrative.run(run_id)
        log.info(f"[{run_id}] pipeline complete")
        await _notify_completion(run_id)
    except Exception as e:
        ...  # unchanged
```

(Phase 7 will slot in here in Task 10 — for now `narrative` remains the last phase.)

- [ ] **Step 3: Smoke-run the existing test suite**

```bash
pytest tests/ -v
```

Expected: all PASS (session wrapping is no-op when opentelemetry isn't present).

- [ ] **Step 4: Commit**

```bash
git add simab/integrations/session.py simab/pipeline.py
git commit -m "feat(observability): wrap each pipeline run in a Phoenix session span"
```

---

## Task 6 — Simulator captures Phoenix span_id per agent

**Files:**
- Modify: `simab/agents/simulator.py` (wrap the Gemini call in a named span; capture span_id)
- Test: extend `tests/test_smoke.py`

- [ ] **Step 1: Write the failing assertion**

Append to `tests/test_smoke.py`:

```python
def test_simresult_serializes_span_id():
    from simab.models import SimResult
    payload = SimResult(
        scenario_id="sc_1", scenario_segment="x",
        agent_idx=0, cohort="variant_a", span_id="span_abc",
    ).model_dump_json()
    assert "span_abc" in payload
```

- [ ] **Step 2: Run the test — it should pass already (covered by Task 2)**

```bash
pytest tests/test_smoke.py::test_simresult_serializes_span_id -v
```

Expected: PASS — this is just defensive coverage.

- [ ] **Step 3: Modify the simulator to start its own span and capture span_id**

Read `simab/agents/simulator.py` and locate the function where one agent calls `generate()` (likely `run_one`). Around that call, wrap with a span and capture the id:

```python
# at the top of simulator.py
try:
    from opentelemetry import trace
    _tracer = trace.get_tracer("simab.simulator")
except ImportError:
    _tracer = None


def _start_agent_span(scenario_id: str, agent_idx: int, cohort: str):
    if _tracer is None:
        @contextlib.contextmanager
        def _noop():
            yield None
        return _noop()
    return _tracer.start_as_current_span(
        name=f"sim_agent.{agent_idx}",
        attributes={
            "veratest.scenario_id": scenario_id,
            "veratest.agent_idx": agent_idx,
            "veratest.cohort": cohort,
        },
    )
```

Add `import contextlib` near the top imports.

Inside `run_one`, wrap the existing `generate(...)` call:

```python
span_id: str | None = None
with _start_agent_span(scenario.id, agent_idx, cohort) as span:
    if span is not None:
        ctx = span.get_span_context()
        span_id = format(ctx.span_id, "016x")
    response = await generate(...)  # existing call, unchanged
```

When constructing the resulting `SimResult`, set the field:

```python
result = SimResult(
    ...,
    span_id=span_id,
)
```

- [ ] **Step 4: Run the suite — verify nothing breaks**

```bash
pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add simab/agents/simulator.py tests/test_smoke.py
git commit -m "feat(simulator): emit per-agent span and persist span_id on SimResult"
```

---

## Task 7 — Phoenix Python client helpers

**Files:**
- Create: `simab/integrations/phoenix_client.py`
- Test: `tests/test_calibration.py` (new file)

This module wraps `phoenix.client.Client` with three safe, mockable functions: query historical persona-drift rate, append drifted-agent rows to a Phoenix Dataset, log SpanEvaluations. Every function degrades to a no-op when Phoenix isn't installed or the API key is missing — so smoke tests and the free tier still work.

- [ ] **Step 1: Create the new test file with the contract we want**

Create `tests/test_calibration.py`:

```python
"""Smoke tests for the Phoenix client helper — no live Phoenix needed."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch


def test_drift_history_returns_empty_when_disabled(monkeypatch):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    from simab.integrations import phoenix_client
    phoenix_client._reset_client_for_test()
    history = phoenix_client.get_persona_drift_history(
        audience_signature="b2b_devtools",
    )
    assert history == {}


def test_append_drifted_agents_is_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    from simab.integrations import phoenix_client
    phoenix_client._reset_client_for_test()
    # Should not raise even with rows.
    phoenix_client.append_drifted_agents(
        run_id="r1",
        rows=[{"persona": "x", "rationale": "y"}],
    )


def test_audience_signature_is_stable():
    from simab.integrations.phoenix_client import audience_signature
    s1 = audience_signature("Startup founders evaluating CI tools")
    s2 = audience_signature("startup founders evaluating ci tools")
    s3 = audience_signature("Different audience")
    assert s1 == s2
    assert s1 != s3
    assert len(s1) <= 64
```

- [ ] **Step 2: Run the test — expect ImportError / ModuleNotFoundError**

```bash
pytest tests/test_calibration.py -v
```

Expected: FAIL (`simab.integrations.phoenix_client` does not exist yet).

- [ ] **Step 3: Create the helper module**

Create `simab/integrations/phoenix_client.py`:

```python
"""Phoenix Python client helpers.

Three things we need from Phoenix at runtime, each safely no-op when the
Phoenix dependency isn't installed or no API key is configured:

1. get_persona_drift_history(audience_signature) -> {archetype: drift_rate}
   Used by ScenarioBuilder to tighten constraints on chronically-drifting
   personas (Gap 2 self-improvement loop).

2. append_drifted_agents(run_id, rows) -> None
   Used by FidelityAuditor to append rows to a persistent Phoenix Dataset
   for the calibration experiment (Refinement 1).

3. log_span_evaluations(eval_name, df) -> None
   Used by FidelityAuditor to attach Span Evaluations to the trace.
"""
from __future__ import annotations
import hashlib
import logging
import re
from typing import Any

from ..config import CONFIG

log = logging.getLogger(__name__)

_client: Any | None = None
_disabled_warned = False


def _reset_client_for_test() -> None:
    """Test hook to drop the cached client between cases."""
    global _client, _disabled_warned
    _client = None
    _disabled_warned = False


def _get_client():
    """Lazily build a phoenix.client.Client. Returns None when unavailable."""
    global _client, _disabled_warned
    if _client is not None:
        return _client
    if not (CONFIG.phoenix_endpoint or CONFIG.phoenix_api_key):
        if not _disabled_warned:
            log.info("Phoenix client disabled — no endpoint or api key set")
            _disabled_warned = True
        return None
    try:
        from phoenix.client import Client
    except ImportError:
        if not _disabled_warned:
            log.warning("Phoenix client not installed — `pip install 'simab[phoenix]'`")
            _disabled_warned = True
        return None
    _client = Client(
        base_url=CONFIG.phoenix_endpoint,
        api_key=CONFIG.phoenix_api_key,
    )
    return _client


def audience_signature(audience: str) -> str:
    """Stable, lowercase, alnum-only hash key for audience grouping.

    We don't want every micro-edit ('CI tools' vs 'CI/CD tooling') to produce
    a different history bucket — a 64-char hash of the normalized audience is
    plenty discriminating without being noisy.
    """
    normalized = re.sub(r"[^a-z0-9 ]+", "", audience.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def get_persona_drift_history(audience_signature: str) -> dict[str, float]:
    """Return {persona_archetype: historical_drift_rate} for past runs of
    the same audience signature. Empty dict when Phoenix is unavailable or
    when there's no prior history.

    Schema: Phoenix Dataset "drifted_agents" rows carry metadata.audience
    and inputs.persona_archetype — we count drift rate per archetype.
    """
    client = _get_client()
    if client is None:
        return {}
    try:
        dataset = client.datasets.get_dataset(name="drifted_agents")
    except Exception as e:
        log.debug(f"drifted_agents dataset not yet present: {e}")
        return {}

    # Sum drift events per archetype, divide by total runs for that audience.
    drift_counts: dict[str, int] = {}
    total_runs_per_archetype: dict[str, int] = {}
    for example in dataset.examples or []:
        meta = example.metadata or {}
        if meta.get("audience_signature") != audience_signature:
            continue
        arche = (example.input or {}).get("persona_archetype", "unknown")
        drift_counts[arche] = drift_counts.get(arche, 0) + 1
        total_runs_per_archetype[arche] = total_runs_per_archetype.get(arche, 0) + 1
    if not drift_counts:
        return {}
    return {a: drift_counts[a] / max(total_runs_per_archetype[a], 1)
            for a in drift_counts}


def append_drifted_agents(*, run_id: str, audience_signature: str,
                          rows: list[dict[str, Any]]) -> None:
    """Append drifted-agent rows to the persistent 'drifted_agents' dataset."""
    if not rows:
        return
    client = _get_client()
    if client is None:
        return
    try:
        client.datasets.append_to_dataset(
            name="drifted_agents",
            inputs=rows,
            metadata=[{"run_id": run_id, "audience_signature": audience_signature}
                      for _ in rows],
        )
    except Exception as e:
        log.warning(f"Failed to append drifted agents to dataset (non-fatal): {e}")


def log_span_evaluations(eval_name: str, df) -> None:
    """Attach Span Evaluations (a pandas DataFrame) to existing traces."""
    client = _get_client()
    if client is None:
        return
    try:
        from phoenix.trace import SpanEvaluations
        client.log_evaluations(SpanEvaluations(eval_name=eval_name, dataframe=df))
    except Exception as e:
        log.warning(f"Failed to log span evaluations '{eval_name}': {e}")
```

- [ ] **Step 4: Run the new tests — they should now pass**

```bash
pytest tests/test_calibration.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add simab/integrations/phoenix_client.py tests/test_calibration.py
git commit -m "feat(phoenix): client helpers for drift history, datasets, span evals"
```

---

## Task 8 — ScenarioBuilder reads drift history + injects stress-test persona

**Files:**
- Modify: `simab/agents/scenarios.py`
- Test: `tests/test_calibration.py` (extend)

This is the self-improvement loop (Gap 2) plus the guaranteed-failure persona (Refinement 4). Both are surgical additions to ScenarioBuilder — they live at the END of its existing pipeline, so we don't disturb the LLM call.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_calibration.py`:

```python
def test_inject_drift_constraints_strengthens_high_drift_personas():
    from simab.agents.scenarios import _inject_drift_constraints
    from simab.models import ScenarioCard

    cards = [
        ScenarioCard(id="sc_1", segment="impulse_buyer", decision_style="impulse"),
        ScenarioCard(id="sc_2", segment="analyst", decision_style="analytical"),
    ]
    history = {"impulse_buyer": 0.40, "analyst": 0.05}
    out = _inject_drift_constraints(cards, history, threshold=0.25)
    impulse = next(c for c in out if c.segment == "impulse_buyer")
    analyst = next(c for c in out if c.segment == "analyst")
    assert any("STAY IN CHARACTER" in c for c in impulse.constraints)
    assert not any("STAY IN CHARACTER" in c for c in analyst.constraints)


def test_inject_stress_test_persona_always_added():
    from simab.agents.scenarios import _inject_stress_test_persona
    from simab.models import ScenarioCard

    cards = [ScenarioCard(id="sc_1", segment="impulse_buyer", traffic_weight=1.0)]
    out = _inject_stress_test_persona(cards)
    stress = [c for c in out if c.segment.startswith("stress_test")]
    assert len(stress) == 1
    # Weights of original cards rebalanced (sum still ~1.0 including stress).
    assert abs(sum(c.traffic_weight for c in out) - 1.0) < 1e-6
```

- [ ] **Step 2: Run the tests — expect ImportError**

```bash
pytest tests/test_calibration.py::test_inject_drift_constraints_strengthens_high_drift_personas tests/test_calibration.py::test_inject_stress_test_persona_always_added -v
```

Expected: FAIL with ImportError.

- [ ] **Step 3: Implement both helpers in scenarios.py**

Open `simab/agents/scenarios.py`. After the existing imports, add:

```python
from ..config import CONFIG
from ..integrations.phoenix_client import (
    audience_signature as _audience_signature,
    get_persona_drift_history,
)


ANTI_DRIFT_CONSTRAINT = (
    "STAY IN CHARACTER. Prior runs show this persona archetype drifts toward "
    "a 'helpful UX evaluator' voice {drift_pct}% of the time. You are NOT a "
    "UX expert. You are this specific person: react in their voice, with "
    "their patience and concerns, NOT a generic professional analysis."
)


def _inject_drift_constraints(
    cards: list[ScenarioCard],
    history: dict[str, float],
    threshold: float,
) -> list[ScenarioCard]:
    """For each card whose archetype has a historical drift rate above
    `threshold`, prepend an anti-drift constraint to its constraints list.
    Returns a new list — does not mutate inputs."""
    out: list[ScenarioCard] = []
    for card in cards:
        drift = history.get(card.segment, 0.0)
        if drift > threshold:
            extra = ANTI_DRIFT_CONSTRAINT.format(drift_pct=int(drift * 100))
            out.append(card.model_copy(update={
                "constraints": [extra, *card.constraints],
            }))
        else:
            out.append(card)
    return out


STRESS_TEST_PERSONA = ScenarioCard(
    id="sc_stress",
    segment="stress_test_conflicted_senior",
    intent="evaluate",
    decision_style="cautious",
    device="desktop",
    traffic_source="referral",
    context=(
        "A 65-year-old who is technologically cautious but is also a former "
        "software developer. They are skeptical of modern marketing aesthetics "
        "but understand technical depth — internal conflict between caution "
        "and expertise."
    ),
    constraints=[
        "Patience for marketing fluff is near zero.",
        "Demand technical specifics before trusting a claim.",
    ],
    time_pressure="medium",
    price_sensitivity="medium",
    patience_threshold="low",
    communication_style="precise, mildly skeptical, occasionally dry",
    visual_style_preference="minimal, dense, technical",
)


def _inject_stress_test_persona(cards: list[ScenarioCard]) -> list[ScenarioCard]:
    """Always include one deliberately-difficult persona so the
    FidelityAuditor has a reliable signal to surface.

    The stress-test persona gets 1/(N+1) weight; existing cards are
    rescaled to (N/(N+1)) of total to keep weights summing to 1.0.
    """
    if not cards:
        return [STRESS_TEST_PERSONA.model_copy(update={"traffic_weight": 1.0})]
    n = len(cards)
    rescale = n / (n + 1)
    weight = 1 / (n + 1)
    rescaled = [c.model_copy(update={"traffic_weight": c.traffic_weight * rescale})
                for c in cards]
    rescaled.append(STRESS_TEST_PERSONA.model_copy(update={"traffic_weight": weight}))
    return rescaled
```

Now wire them into the existing `run()` function. Find where the final list of scenarios is written (look for `write_scenarios(...)`). Just before that call, add:

```python
# Calibration layer — read cross-run drift history and tighten constraints.
sig = _audience_signature(run.brief.audience if run.brief else run.audience_raw)
history = get_persona_drift_history(audience_signature=sig)
scenarios = _inject_drift_constraints(
    scenarios, history, threshold=CONFIG.fidelity_drift_threshold,
)

# Always include one stress-test persona so the FidelityAuditor has signal.
scenarios = _inject_stress_test_persona(scenarios)
```

(`scenarios` is the variable name used in the existing function; if it's different, adapt locally — do not invent new names.)

- [ ] **Step 4: Run the tests — they should now pass**

```bash
pytest tests/test_calibration.py tests/test_smoke.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add simab/agents/scenarios.py tests/test_calibration.py
git commit -m "feat(scenarios): drift-history-driven anti-drift constraint + stress-test persona"
```

---

## Task 9 — Phase 7 FidelityAuditor (LLM-as-a-Judge + code-based eval)

**Files:**
- Create: `simab/agents/fidelity.py`
- Test: `tests/test_fidelity.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_fidelity.py`:

```python
"""Smoke tests for the FidelityAuditor — mocks the Phoenix evals call."""
from __future__ import annotations
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import pandas as pd


@pytest.mark.asyncio
async def test_fidelity_computes_persona_consistency_and_coherence(tmp_path,
                                                                   monkeypatch):
    monkeypatch.setenv("SIMAB_DB_PATH", str(tmp_path / "test.db"))
    from simab import state
    from simab.agents import fidelity
    from simab.models import ScenarioCard, SimResult, Brief
    state._db = None

    rid = await state.create_run(
        goal="g", audience_raw="b2b", persona_source="paste",
        variant_a_path="/a.png", variant_b_path=None,
    )
    await state.write_brief(rid, Brief(
        conversion_goal="g", variant_a_summary="x",
        inferred_personas=[],
    ))
    sc = ScenarioCard(id="sc_1", segment="impulse_buyer")
    await state.write_scenarios(rid, [sc], allocations=[])
    # Two sim results: one in-character w/ coherent score, one drifted w/ incoherent.
    await state.append_sim_result(rid, SimResult(
        scenario_id="sc_1", scenario_segment="impulse_buyer",
        agent_idx=0, cohort="variant_a",
        resonance={"motivation": 3, "identity": 4, "situation": 3,
                   "beliefs": 3, "ability": 4, "trigger": 3},
        resonance_overall=3.3,
        metacognitive_reflection="I felt confused and frustrated by the dense copy.",
    ))
    await state.append_sim_result(rid, SimResult(
        scenario_id="sc_1", scenario_segment="impulse_buyer",
        agent_idx=1, cohort="variant_a",
        resonance={"motivation": 9, "identity": 9, "situation": 9,
                   "beliefs": 9, "ability": 9, "trigger": 9},
        resonance_overall=9.0,
        metacognitive_reflection=(
            "As an AI, I notice this page is confusing and frustrating, "
            "the user would find it overwhelming."
        ),
    ))

    fake_results = pd.DataFrame([
        {"label": "in_character", "explanation": "stayed in voice"},
        {"label": "drifted",      "explanation": "used 'as an AI' phrasing"},
    ])
    with patch("simab.agents.fidelity.llm_classify",
               return_value=fake_results) as mock_classify, \
         patch("simab.agents.fidelity.log_span_evaluations") as mock_log, \
         patch("simab.agents.fidelity.append_drifted_agents") as mock_append:
        await fidelity.run(rid)

    mock_classify.assert_called_once()
    mock_log.assert_called()
    mock_append.assert_called()

    run = await state.get_run(rid)
    assert run is not None
    assert run.fidelity is not None
    assert run.fidelity.persona_consistency == 0.5  # 1 of 2 in-character
    assert run.fidelity.agents_drifted == 1
    # Code-based coherence eval — high score + negative rationale = incoherent.
    assert run.fidelity.agents_incoherent >= 1
    assert run.status == "complete"
    await state.close_db()
```

- [ ] **Step 2: Run the test — expect ModuleNotFoundError**

```bash
pytest tests/test_fidelity.py -v
```

Expected: FAIL — `simab.agents.fidelity` does not exist.

- [ ] **Step 3: Create the FidelityAuditor**

Create `simab/agents/fidelity.py`:

```python
"""Phase 7 · FidelityAuditor — LLM-as-a-Judge persona consistency
plus a code-based score/rationale coherence check.

Writes:
 - SpanEvaluations to Phoenix (`persona_consistency`, `rationale_coherence`)
 - Drifted rows into the Phoenix `drifted_agents` Dataset
 - The `Run.fidelity` slice
 - status -> complete (replaces narrative as the terminal phase)

The base architecture's open/closed rule still holds: this agent reads
sim_results + scenarios, writes only its own slice + cross-run Phoenix data.
"""
from __future__ import annotations
import logging
from typing import Iterable

import pandas as pd

from .. import state
from ..config import CONFIG
from ..integrations.phoenix_client import (
    append_drifted_agents,
    audience_signature,
    log_span_evaluations,
)
from ..models import FidelityReport, SimResult

log = logging.getLogger(__name__)


PERSONA_CONSISTENCY_TEMPLATE = """\
You are auditing whether a simulated user stayed in character.

PERSONA THIS AGENT WAS ASSIGNED:
{persona}

WHAT THE AGENT ACTUALLY WROTE:
{rationale}

Did the agent reason as this specific persona (with their stated patience,
decision style, and concerns), or did it slip into a generic "helpful UX
expert" voice?

Respond with exactly one word: "in_character" or "drifted".
"""

RAILS = ["in_character", "drifted"]


# Cheap deterministic markers for the code-based eval (Refinement 2).
_NEGATIVE_MARKERS = (
    "confusing", "unclear", "frustrat", "would leave", "too much",
    "overwhelm", "doesn't trust", "skeptical", "abandon", "give up",
)


def _is_incoherent(sr: SimResult) -> bool:
    """Code-based eval: numeric score direction must match rationale tone.

    - High score (avg >= 7) with multiple negative markers -> incoherent.
    - Low score (avg <= 4) with zero negative markers      -> incoherent.
    - Otherwise coherent.

    Deterministic, runs in microseconds, can't hallucinate.
    """
    if not sr.resonance:
        return False
    avg = sum(sr.resonance.values()) / len(sr.resonance)
    text = (sr.metacognitive_reflection or sr.rationale or "").lower()
    negative_hits = sum(1 for m in _NEGATIVE_MARKERS if m in text)
    if avg >= 7 and negative_hits >= 2:
        return True
    if avg <= 4 and negative_hits == 0:
        return True
    return False


# Imported lazily so that smoke tests can patch them without requiring the
# arize-phoenix-evals dep at import time.
def llm_classify(*args, **kwargs):  # pragma: no cover - thin re-export
    from phoenix.evals import llm_classify as _llm_classify
    return _llm_classify(*args, **kwargs)


def _gemini_model():  # pragma: no cover - real-Phoenix path only
    from phoenix.evals import GeminiModel
    return GeminiModel(model="gemini-2.5-flash")


def _build_persona_summary(scenario) -> str:
    parts = [
        f"Segment: {scenario.segment}",
        f"Intent: {scenario.intent}",
        f"Decision style: {scenario.decision_style}",
        f"Patience: {scenario.patience_threshold}",
        f"Communication style: {scenario.communication_style or 'n/a'}",
        f"Context: {scenario.context or 'n/a'}",
    ]
    return "\n".join(parts)


async def run(run_id: str) -> None:
    await state.set_status(run_id, "calibrating")
    run = await state.get_run(run_id)
    if run is None or not run.simulation_results:
        log.warning(f"[{run_id}] FidelityAuditor: no sim results, skipping")
        await state.set_status(run_id, "complete")
        return

    scenarios_by_id = {s.id: s for s in run.scenarios}

    # --- LLM-as-a-Judge: persona consistency -------------------------------
    rows = []
    for sr in run.simulation_results:
        scenario = scenarios_by_id.get(sr.scenario_id)
        if scenario is None:
            continue
        rows.append({
            "span_id": sr.span_id or "",
            "persona": _build_persona_summary(scenario),
            "rationale": sr.metacognitive_reflection or sr.rationale or "",
            "persona_archetype": scenario.segment,
            "agent_idx": sr.agent_idx,
            "scenario_id": sr.scenario_id,
        })
    df = pd.DataFrame(rows)

    try:
        results = llm_classify(
            data=df,
            model=_gemini_model(),
            template=PERSONA_CONSISTENCY_TEMPLATE,
            rails=RAILS,
            provide_explanation=True,
            concurrency=6,
        )
    except Exception as e:
        log.warning(f"[{run_id}] llm_classify failed (non-fatal): {e}")
        results = pd.DataFrame({"label": ["in_character"] * len(df),
                                "explanation": [""] * len(df)})

    # Combine input and label so we can score persona_consistency.
    merged = df.join(results.reset_index(drop=True))
    merged["score"] = (merged["label"] == "in_character").astype(int)
    persona_consistency = float(merged["score"].mean()) if len(merged) else 1.0
    drifted_idx = merged.loc[merged["label"] == "drifted", "agent_idx"].tolist()
    explanations = merged["explanation"].tolist() if "explanation" in merged else []

    log_span_evaluations(
        eval_name="persona_consistency",
        df=merged[["span_id", "label", "score", "explanation"]]
            .rename(columns={"span_id": "context.span_id"}),
    )

    # --- Code-based eval: rationale coherence ------------------------------
    incoherent: list[int] = []
    coh_rows = []
    for sr in run.simulation_results:
        bad = _is_incoherent(sr)
        if bad:
            incoherent.append(sr.agent_idx)
        coh_rows.append({
            "context.span_id": sr.span_id or "",
            "label": "incoherent" if bad else "coherent",
            "score": 0 if bad else 1,
        })
    rationale_coherence = 1.0 - (len(incoherent) / max(len(run.simulation_results), 1))
    log_span_evaluations(eval_name="rationale_coherence", df=pd.DataFrame(coh_rows))

    # --- Append drifted rows to persistent Phoenix Dataset -----------------
    sig = audience_signature(
        run.brief.conversion_goal if run.brief else run.goal
    )
    drifted_rows = [
        {"persona": r["persona"], "rationale": r["rationale"],
         "persona_archetype": r["persona_archetype"],
         "scenario_id": r["scenario_id"]}
        for r, label in zip(rows, merged["label"].tolist())
        if label == "drifted"
    ]
    append_drifted_agents(
        run_id=run_id, audience_signature=sig, rows=drifted_rows,
    )

    # --- Write the fidelity slice and finalize -----------------------------
    report = FidelityReport(
        persona_consistency=round(persona_consistency, 4),
        agents_drifted=len(drifted_idx),
        rationale_coherence=round(rationale_coherence, 4),
        agents_incoherent=len(incoherent),
        eval_explanations=[e for e in explanations if e][:20],
        drifted_agent_indices=drifted_idx,
    )
    await state.write_fidelity(run_id, report)
    await state.set_status(run_id, "complete")
    log.info(
        f"[{run_id}] fidelity: persona_consistency={persona_consistency:.2f} "
        f"coherence={rationale_coherence:.2f}"
    )
```

- [ ] **Step 4: Run the tests — they should now pass**

```bash
pytest tests/test_fidelity.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add simab/agents/fidelity.py tests/test_fidelity.py
git commit -m "feat(fidelity): Phase 7 FidelityAuditor — LLM-as-a-Judge + code eval + Phoenix writes"
```

---

## Task 10 — Wire Phase 7 into the pipeline

**Files:**
- Modify: `simab/pipeline.py`

- [ ] **Step 1: Add the import and the new phase call**

Read `simab/pipeline.py`. Replace the import line:

```python
from .agents import auditor, narrative, normalizer, scenarios, simulator, synthesizer
```

with:

```python
from .agents import (
    auditor, fidelity, narrative, normalizer, scenarios, simulator, synthesizer,
)
```

Inside `run_pipeline`, add the fidelity phase after `narrative`:

```python
with run_session(run_id):
    await normalizer.run(run_id)
    await scenarios.run(run_id)
    await _run_simulators(run_id)
    await auditor.run(run_id)
    await synthesizer.run(run_id)
    await narrative.run(run_id)
    await fidelity.run(run_id)   # Phase 7 — sets status=complete
```

The synthesizer / narrative agents must no longer call `set_status(..., "complete")`. Verify:

```bash
grep -nE "set_status.*complete" simab/agents/*.py
```

If `narrative.py` or `synthesizer.py` calls `set_status(..., "complete")`, change those to leave the status as `synthesizing` / `narrating` — fidelity now owns the terminal status.

- [ ] **Step 2: Smoke-test the full suite**

```bash
pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add simab/pipeline.py simab/agents/narrative.py simab/agents/synthesizer.py
git commit -m "feat(pipeline): add Phase 7 fidelity; narrative/synthesizer no longer terminal"
```

---

## Task 11 — Calibration experiment script (Refinement 1)

**Files:**
- Create: `scripts/run_calibration_experiment.py`

This is the standalone script you run before the demo recording. It pulls the persistent `drifted_agents` Dataset, runs the baseline SimAgent prompt against it, then runs the tightened prompt, and prints/links the resulting Phoenix Experiments side by side. **This is what creates the visible 78% → 94% in the video.**

- [ ] **Step 1: Create the script**

```bash
mkdir -p scripts
```

Create `scripts/run_calibration_experiment.py`:

```python
"""Run a Phoenix Experiment comparing baseline vs tightened SimAgent prompts.

Pre-conditions:
  * Phoenix Cloud or self-hosted instance reachable via PHOENIX_COLLECTOR_ENDPOINT.
  * The `drifted_agents` dataset has been populated by at least one prior run
    where the FidelityAuditor detected drift.

Run:
    python -m scripts.run_calibration_experiment

Output:
    Prints the URLs of the two Phoenix Experiments — open both in the UI to
    see the side-by-side fidelity comparison referenced in the demo video.
"""
from __future__ import annotations
import asyncio
import logging
import sys

from simab.agents.fidelity import (
    PERSONA_CONSISTENCY_TEMPLATE, RAILS, _gemini_model,
)
from simab.integrations.phoenix import init_phoenix

log = logging.getLogger(__name__)


BASELINE_TEMPLATE = "{persona}\n\nRespond as this persona. {rationale}"

TIGHTENED_TEMPLATE = (
    "STAY IN CHARACTER. You are NOT a UX expert. You are this specific person.\n\n"
    "{persona}\n\n"
    "React as this persona would. Do NOT say 'as an AI' or analyze. "
    "Respond in first person, in their voice. {rationale}"
)


def _judge(input_row: dict) -> dict:
    """Evaluator: run the LLM-as-a-Judge persona-consistency check on a row."""
    import pandas as pd
    from phoenix.evals import llm_classify
    df = pd.DataFrame([{"persona": input_row.get("persona", ""),
                        "rationale": input_row.get("rationale", "")}])
    out = llm_classify(
        data=df, model=_gemini_model(),
        template=PERSONA_CONSISTENCY_TEMPLATE,
        rails=RAILS, provide_explanation=True,
    )
    label = out["label"].iloc[0]
    return {"score": 1 if label == "in_character" else 0, "label": label}


def _make_task(template: str):
    """Wrap a prompt template as a Phoenix task: takes a row, returns text."""
    from simab.llm import MODEL_FLASH_LITE, generate

    async def _task(row: dict) -> str:
        prompt = template.format(
            persona=row.get("persona", ""),
            rationale=row.get("rationale", ""),
        )
        return await generate(model=MODEL_FLASH_LITE, prompt=prompt)
    return _task


async def main() -> int:
    init_phoenix()
    try:
        from phoenix.client import Client
        from phoenix.experiments import run_experiment
    except ImportError:
        print("phoenix-client + phoenix-experiments not installed. "
              "Run: pip install 'simab[phoenix]'", file=sys.stderr)
        return 1

    client = Client()
    try:
        dataset = client.datasets.get_dataset(name="drifted_agents")
    except Exception as e:
        print(f"drifted_agents dataset missing: {e}\n"
              "Run at least one pretest that produces drift before calibrating.",
              file=sys.stderr)
        return 1

    baseline = await run_experiment(
        dataset=dataset,
        task=_make_task(BASELINE_TEMPLATE),
        evaluators=[_judge],
        experiment_name="sim_agent_baseline",
    )
    tightened = await run_experiment(
        dataset=dataset,
        task=_make_task(TIGHTENED_TEMPLATE),
        evaluators=[_judge],
        experiment_name="sim_agent_tightened_v2",
    )
    print(f"Baseline experiment:  {baseline.url if hasattr(baseline, 'url') else baseline.id}")
    print(f"Tightened experiment: {tightened.url if hasattr(tightened, 'url') else tightened.id}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 2: Sanity-check the script imports cleanly without running**

```bash
python -c "import scripts.run_calibration_experiment as s; print(hasattr(s, 'main'))"
```

Expected: `True` (no ImportError).

- [ ] **Step 3: Commit**

```bash
git add scripts/run_calibration_experiment.py
git commit -m "feat(experiments): calibration script for baseline-vs-tightened demo"
```

---

## Task 12 — Phoenix MCP server config + README docs

**Files:**
- Create: `mcp/phoenix-mcp.example.json`
- Modify: `README.md`

The Arize track explicitly requires the agent to introspect its own operational data **via the Phoenix MCP server**. Our pipeline reads Phoenix via the Python client (Tasks 8-9), which handles the *data access*. The MCP server is the *interface compliance* piece: it lets a user (or another agent) hold a conversation with our system and ask things like *"which personas drifted last week?"* through any MCP client.

- [ ] **Step 1: Create the example config**

Create `mcp/phoenix-mcp.example.json`:

```jsonc
{
  "mcpServers": {
    "veratest": {
      "command": "python",
      "args": ["-m", "simab_mcp"],
      "env": { "SIMAB_API_URL": "http://localhost:8000" }
    },
    "phoenix": {
      "command": "npx",
      "args": ["-y", "@arizeai/phoenix-mcp@latest"],
      "env": {
        "PHOENIX_BASE_URL": "http://localhost:6006",
        "PHOENIX_API_KEY":  ""
      }
    }
  }
}
```

- [ ] **Step 2: Add a README section pointing to it**

In `README.md`, locate the existing `## MCP tools` heading. After the existing `run_pretest` / `get_pretest_result` / `list_runs` / `list_personas` table, append:

```markdown
### Phoenix MCP — runtime introspection of your own traces

The Arize track requires agents to introspect their operational data at
runtime via the Phoenix MCP server. Drop this into any MCP client config —
Claude Desktop, Gemini CLI, Cursor — alongside the VeraTest MCP server:

\`\`\`bash
cp mcp/phoenix-mcp.example.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
\`\`\`

Then ask Claude (or Gemini CLI):

> *"Which personas drifted in the last 5 VeraTest runs, and what was their
> average rationale coherence?"*

The Phoenix MCP server exposes Datasets, Experiments, Prompts, and Spans
as MCP tools — so your assistant can query them directly, no SQL required.
```

(Escape the inline `\`\`\`` blocks correctly when committing — the example above is for clarity.)

- [ ] **Step 3: Commit**

```bash
git add mcp/phoenix-mcp.example.json README.md
git commit -m "docs(mcp): document Phoenix MCP server config and runtime introspection"
```

---

## Task 13 — Frontend fidelity badge in CommandRail

**Files:**
- Modify: `frontend/app/runs/[id]/page.tsx`
- Modify: `frontend/app/runs/[id]/components/CommandRail.tsx`

The gap doc is explicit: *"the PM Command Center gets a new validity signal — '19/20 agents stayed in persona (95% fidelity).' That number is the answer to 'how do I trust this?' It belongs in the CommandRail next to the coverage badge."*

- [ ] **Step 1: Pass fidelity into CommandRail**

In `frontend/app/runs/[id]/page.tsx`, find where `<CommandRail ... />` is rendered. Add the prop:

```tsx
<CommandRail
  ...existing props...
  fidelity={run.fidelity ?? null}
/>
```

- [ ] **Step 2: Render the badge in CommandRail**

In `frontend/app/runs/[id]/components/CommandRail.tsx`, add to the props type:

```ts
fidelity?: {
  persona_consistency: number;
  agents_drifted: number;
  rationale_coherence: number;
  agents_incoherent: number;
} | null;
```

In the component body (near where the coverage badge is rendered), add:

```tsx
{fidelity && (
  <div
    title={`${fidelity.agents_drifted} agents drifted; ${fidelity.agents_incoherent} incoherent`}
    className="flex items-center gap-1.5 text-xs font-medium rounded-full bg-emerald-500/10 text-emerald-700 px-2 py-1"
  >
    <span aria-hidden>◉</span>
    {Math.round(fidelity.persona_consistency * 100)}% in character
  </div>
)}
```

(Style classes are the Tailwind tokens the rest of CommandRail already uses; copy from a neighboring badge if these are wrong.)

- [ ] **Step 3: Type-check the frontend**

```bash
cd frontend && npx tsc --noEmit && cd ..
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/runs/[id]/page.tsx \
        frontend/app/runs/[id]/components/CommandRail.tsx
git commit -m "feat(ui): fidelity badge in CommandRail — answers the trust question"
```

---

## Task 14 — Exports include fidelity

**Files:**
- Modify: `simab/exports.py`
- Test: `tests/test_exports.py` (extend)

- [ ] **Step 1: Add a test for the markdown export**

In `tests/test_exports.py`, append:

```python
def test_markdown_export_includes_fidelity_when_present():
    from simab.exports import markdown_export
    from simab.models import Run, FidelityReport
    run = _minimal_complete_run()  # use whatever helper already exists in the test
    run.fidelity = FidelityReport(persona_consistency=0.95, agents_drifted=1)
    md = markdown_export(run)
    assert "95% in character" in md or "Fidelity" in md
```

If `_minimal_complete_run()` doesn't already exist in `tests/test_exports.py`, build a minimal one inline matching the existing fixtures.

- [ ] **Step 2: Add a Fidelity section to the markdown export**

In `simab/exports.py`, find the function that emits the existing report (e.g. `markdown_export(run)`). Add a small section before the closing line:

```python
if run.fidelity:
    fid = run.fidelity
    pct = round(fid.persona_consistency * 100)
    lines.append("")
    lines.append("## Calibration / fidelity")
    lines.append(f"- **Persona consistency:** {pct}% in character "
                 f"({fid.agents_drifted} drifted)")
    lines.append(f"- **Rationale coherence:** "
                 f"{round(fid.rationale_coherence * 100)}% coherent "
                 f"({fid.agents_incoherent} incoherent)")
```

- [ ] **Step 3: Run the tests**

```bash
pytest tests/test_exports.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add simab/exports.py tests/test_exports.py
git commit -m "feat(exports): include fidelity section in markdown report"
```

---

## Task 15 — README + CLAUDE.md sweep

**Files:**
- Modify: `README.md` (drop competing-platform refs · add no-framework defense · add fidelity story)
- Modify: `CLAUDE.md`

- [ ] **Step 1: Drop Hugging Face / Render references from README**

```bash
grep -nE "Hugging Face|Spaces|Render" README.md
```

Remove any sections that advertise Hugging Face Spaces or Render. Cloud Run only.

- [ ] **Step 2: Add the no-framework defense paragraph (Refinement 5)**

In `README.md`, find the existing line *"No LangChain. No LangGraph. No framework."* Replace it with a fuller paragraph:

```markdown
**Why no agent framework?** VeraTest deliberately uses none. The pipeline
coordinates through a single shared SQLite document — every agent reads
from and writes to one structured record — so each run is fully
inspectable, every decision is debuggable, and there's no framework
abstraction between you and the agent behavior. This is exactly the
transparency Phoenix tracing is designed for: every Gemini call is a
direct OpenInference span, with no framework intermediation to obscure
what the agent saw and decided.
```

- [ ] **Step 3: Add a fidelity / calibration section to README**

After the existing "Phoenix" section, add:

```markdown
### Cross-run calibration — agents that improve

A 7th agent — **FidelityAuditor** — runs an LLM-as-a-Judge persona-
consistency eval plus a code-based rationale-coherence check on every run.
Drifted agents are written to a persistent Phoenix Dataset; on the next
run targeting a similar audience, ScenarioBuilder queries that history and
strengthens the prompt of any persona archetype that has drifted >25% of
the time. The Command Center surfaces this as a "95% in character" badge —
the answer to "how do I trust this?"

See [scripts/run_calibration_experiment.py](scripts/run_calibration_experiment.py)
for the baseline-vs-tightened Phoenix Experiment that produces the
visible before/after fidelity delta.
```

- [ ] **Step 4: Update CLAUDE.md pipeline diagram + agent table**

In `CLAUDE.md`, locate the stigmergy pipeline arrow diagram and the agent slice table. Add a 7th row to the table:

```markdown
| **FidelityAuditor** | `fidelity.py` | `run.simulation_results`, `run.scenarios` | `run.fidelity`, sets status=**complete** |
```

And extend the diagram:

```
Upload → Study Designer → Panel Recruiter → 20 × Cognitive Walkers → Bias Auditor → Insight Analyst → Report Narrators (×3) → Fidelity Auditor
```

Add a note under "Single-screen mode" that the FidelityAuditor still runs (it operates on persona/rationale, not on the variant comparison).

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: no-framework defense, fidelity story, drop competing platforms"
```

---

## Task 16 — Final integration check

**Files:**
- All

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: 35+ PASS (31 original + new fidelity / calibration / smoke tests).

- [ ] **Step 2: Verify frontend type-check**

```bash
cd frontend && npx tsc --noEmit && cd ..
```

Expected: no errors.

- [ ] **Step 3: Boot the backend, run one end-to-end pretest (no Phoenix)**

```bash
export GEMINI_API_KEY=$GEMINI_API_KEY
uvicorn simab.main:app --port 8000 &
sleep 3
RID=$(curl -s -X POST http://localhost:8000/api/runs \
  -F "variant_a=@tests/fixtures/variant_a.png" \
  -F "goal=sign up for free trial" \
  -F "audience=Startup founders evaluating CI tools" | python -c "import json,sys;print(json.load(sys.stdin)['run_id'])")
echo "RUN: $RID"

# Poll until complete (or fail) — bounded retries
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  STATUS=$(curl -s http://localhost:8000/api/runs/$RID | python -c "import json,sys;print(json.load(sys.stdin)['status'])")
  echo "[$i] status=$STATUS"
  [ "$STATUS" = "complete" ] || [ "$STATUS" = "failed" ] && break
  sleep 5
done

curl -s http://localhost:8000/api/runs/$RID | python -c "import json,sys;r=json.load(sys.stdin);print('fidelity:', r.get('fidelity'))"
kill %1
```

Expected: final status `complete`; `fidelity` slice is non-null with `persona_consistency` between 0.0 and 1.0.

- [ ] **Step 4: With Phoenix Cloud configured, repeat the e2e run**

```bash
export PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
export PHOENIX_API_KEY=<your-cloud-key>
export PHOENIX_PROJECT=veratest
# (re-run Step 3)
```

Expected: in the Phoenix UI under the `veratest` project, one Session per run with all spans nested; SpanEvaluations for `persona_consistency` and `rationale_coherence` visible; the `drifted_agents` Dataset shows new rows.

- [ ] **Step 5: Run the calibration experiment**

```bash
python -m scripts.run_calibration_experiment
```

Expected: prints two Phoenix Experiment URLs; opening them in the UI shows side-by-side fidelity scores for `sim_agent_baseline` vs `sim_agent_tightened_v2`.

---

## Out of scope (deliberately deferred)

- **Refinement 6 — Phoenix Prompts versioning.** Useful polish for the demo but adds dependency on the prompt-management API and is straightforward to add later. Skip unless time permits after Task 16.
- **BiasAuditor cross-run baselines.** The gap doc proposes giving the BiasAuditor access to historical motivation/ability score means via Phoenix MCP. The ScenarioBuilder loop (Task 8) already exercises the cross-run-memory pattern judges look for — adding it to BiasAuditor too is incremental, not foundational. Defer to a follow-up plan if reviewers ask for it.
- **Removing legacy v0.2 fields.** The plan touches `SimResult` and `Run` but does not refactor any existing fields. Stays as-is.
- **N-variant mode and Figma plugin** — already roadmap items, untouched here.

---

## Self-review

**Spec coverage:**

| Gap / refinement | Task |
|---|---|
| Gap 1 — Phoenix MCP introspection | 12 (MCP config + docs); cross-run reads happen via Python client in 8 / 9 |
| Gap 2 — Self-improvement loop | 8 (scenarios reads drift history), 11 (experiment script visualizes it) |
| Gap 3 — LLM-as-a-Judge evals | 9 (FidelityAuditor) |
| Refinement 1 — Datasets + Experiments | 9 (`append_drifted_agents`), 11 (experiment script) |
| Refinement 2 — Code-based eval | 9 (`_is_incoherent`) |
| Refinement 3 — Phoenix Session per run | 5 |
| Refinement 4 — Stress-test persona | 8 (`_inject_stress_test_persona`) |
| Refinement 5 — No-framework defense | 15 |
| Refinement 6 — Phoenix Prompts versioning | Out of scope |
| OpenInference auto-instrumentor | Already present in `simab/integrations/phoenix.py`; wired via Task 4 |
| `init_phoenix` is dead code | Task 4 |
| Drop competing-platform refs | Task 15 |
| Model + state additions | Tasks 2, 3 |
| Fidelity badge in CommandRail | Task 13 |
| Markdown / PM export | Task 14 |

All in-scope items have at least one task. The two MCP roles (Python client for in-pipeline reads vs Phoenix MCP server for client-facing introspection) are addressed separately by Tasks 7 + 12.

**Type consistency check:**

- `FidelityReport` field names are identical across Task 2 (definition), Task 9 (writer), Task 13 (frontend prop), Task 14 (export): `persona_consistency`, `agents_drifted`, `rationale_coherence`, `agents_incoherent`, `eval_explanations`, `drifted_agent_indices`.
- `audience_signature(...)` is defined once in `phoenix_client.py` (Task 7) and imported in both `scenarios.py` (Task 8) and `fidelity.py` (Task 9).
- `RunStatus = "calibrating"` is added in Task 2; used in Task 9 (`set_status(..., "calibrating")`).
- `state.write_fidelity` defined in Task 3; called in Task 9.
- `phoenix_client.get_persona_drift_history`, `append_drifted_agents`, `log_span_evaluations` defined in Task 7; consumed in Tasks 8 and 9.

**Placeholder scan:** Steps reference real file paths, real model field names, and concrete code. The one place a reader has to peek at the existing code is Task 4 Step 2 (find the FastAPI `app =` line) and Task 8 Step 3 (find `write_scenarios(...)` site) — both are 30-second `grep` lookups guarded with the exact pattern in the step.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-arize-track-calibration-layer.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task with two-stage review (plan → patch → test → review → next task). Best for a 16-task plan touching backend, frontend, MCP, and docs because each task gets focused context.

**2. Inline Execution** — run tasks in this session in batches with checkpoints (e.g. Tasks 1-3 → review → 4-6 → review → ...). Faster if you want to steer constantly, harder on context.

Which approach?
