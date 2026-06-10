"""FastAPI app — three surfaces over one backend.

Endpoints:
  REST API   POST /api/runs                 create + start a run
             GET  /api/runs/{id}            fetch run state
             GET  /api/runs/{id}/stream     SSE progress stream
             GET  /api/runs                 list recent runs
             GET  /api/personas             list saved personas

  A2A       POST /a2a/v1/tasks              A2A-protocol task submission
            GET  /a2a/v1/tasks/{id}         A2A-protocol result fetch
            GET  /.well-known/agent-card.json   discovery

The MCP server hits the REST API; it does not need its own endpoints here.
"""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Optional
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from . import exports, ratelimit, state
from .config import CONFIG
from .integrations.phoenix import init_phoenix
from .models import AudiencePreset, CreateRunResponse
from .pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(CONFIG.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(CONFIG.db_path).parent.mkdir(parents=True, exist_ok=True)
    await state.get_db()  # initialize schema
    init_phoenix()  # OpenInference tracing — no-op when PHOENIX_* env not set
    from . import agent_runtime
    agent_runtime.warmup()  # build the ADK Runner once; no-op without [agent]
    yield
    await state.close_db()


app = FastAPI(title="SimAB", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CONFIG.frontend_url, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ratelimit.RateLimitMiddleware)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

def _safe_upload_name(filename: Optional[str]) -> str:
    """Reduce a client-supplied filename to a bare basename.

    Browsers send plain names, but the field is client-controlled — strip any
    directory components so the stored path can never resolve outside
    CONFIG.upload_dir. Note Path("..").name is ".." (not ""), so dot names
    need an explicit reject.
    """
    name = Path(filename or "").name
    return "upload.png" if name in ("", ".", "..") else name


@app.post("/api/runs", response_model=CreateRunResponse, status_code=201)
async def create_run(
    background_tasks: BackgroundTasks,
    variant_a: UploadFile,
    variant_b: Optional[UploadFile] = None,
    goal: str = Form(...),
    audience: str = Form(""),
    audience_preset: str = Form(""),
    persona_source: str = Form("paste"),
) -> CreateRunResponse:
    """Create a run and kick off the pipeline in the background.

    variant_b is optional — omit it for single-screen design analysis.
    """
    if not variant_a:
        raise HTTPException(status_code=400, detail="variant_a is required")

    # Save uploads to disk
    upload_root = Path(CONFIG.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    suffix = uuid.uuid4().hex[:8]
    a_path = upload_root / f"{suffix}_a_{_safe_upload_name(variant_a.filename)}"
    a_path.write_bytes(await variant_a.read())
    b_path_str: Optional[str] = None
    if variant_b:
        b_path = upload_root / f"{suffix}_b_{_safe_upload_name(variant_b.filename)}"
        b_path.write_bytes(await variant_b.read())
        b_path_str = str(b_path)

    # Parse audience_preset JSON if provided. Empty string means "no preset".
    preset_obj: AudiencePreset | None = None
    if audience_preset:
        try:
            preset_obj = AudiencePreset.model_validate_json(audience_preset)
            if preset_obj.is_empty():
                preset_obj = None
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid audience_preset JSON: {e}")
    if preset_obj is not None and persona_source == "paste":
        persona_source = "preset"

    run_id = await state.create_run(
        goal=goal,
        audience_raw=audience,
        audience_preset=preset_obj,
        persona_source=persona_source,
        variant_a_path=str(a_path),
        variant_b_path=b_path_str,
    )

    # Run in background — Cloud Run / uvicorn handle async tasks fine
    background_tasks.add_task(run_pipeline, run_id)

    return CreateRunResponse(
        run_id=run_id,
        status="pending",
        stream_url=f"/api/runs/{run_id}/stream",
        dashboard_url=f"{CONFIG.frontend_url}/runs/{run_id}",
    )


# ---------------------------------------------------------------------------
# Agent ("describe it" mode) — natural-language front door to the pipeline.
# One multipart turn: upload the screenshot(s) + free-text description, and the
# ADK Concierge agent parses it and starts a pretest in a single round-trip.
# ---------------------------------------------------------------------------

@app.post("/api/agent/run")
async def agent_run(
    variant_a: UploadFile,
    description: str = Form(...),
    variant_b: Optional[UploadFile] = None,
) -> dict:
    """Parse a free-text description + screenshot(s) and start a pretest.

    Returns {"run_id": ...} on success (page redirects to /runs/{id}), or
    {"needs_clarification": True, "question": ...} if the agent needs more info.

    On clarification or failure no run is created, so the just-saved uploads are
    orphans — delete them before returning so the upload dir doesn't accumulate
    abandoned files on every retry.
    """
    description = (description or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="description is required")
    if not variant_a:
        raise HTTPException(status_code=400, detail="variant_a is required")

    upload_root = Path(CONFIG.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    suffix = uuid.uuid4().hex[:8]
    a_path = upload_root / f"{suffix}_a_{_safe_upload_name(variant_a.filename)}"
    a_path.write_bytes(await variant_a.read())
    b_path: Optional[Path] = None
    if variant_b:
        b_path = upload_root / f"{suffix}_b_{_safe_upload_name(variant_b.filename)}"
        b_path.write_bytes(await variant_b.read())

    def _cleanup_orphans() -> None:
        a_path.unlink(missing_ok=True)
        if b_path is not None:
            b_path.unlink(missing_ok=True)

    from . import agent_runtime
    try:
        result = await agent_runtime.launch_from_description(
            description, str(a_path), str(b_path) if b_path else None
        )
    except Exception as e:
        # Surface the real cause to the UI instead of an opaque 500 — the agent
        # turn can fail on Vertex auth, model errors, or an MCP tool hiccup.
        _cleanup_orphans()
        log.exception("agent run failed")
        raise HTTPException(
            status_code=503, detail=f"{type(e).__name__}: {e}"[:400]
        )

    if result.get("run_id"):
        result["dashboard_url"] = f"{CONFIG.frontend_url}/runs/{result['run_id']}"
    else:
        # needs_clarification — uploads are orphaned until the user retries.
        _cleanup_orphans()
    return result


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = await state.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return json.loads(run.model_dump_json())


@app.get("/api/runs")
async def list_runs(limit: int = 50) -> list[dict]:
    runs = await state.list_runs(limit=limit)
    return [json.loads(r.model_dump_json()) for r in runs]


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    """Server-Sent Events stream of run progress.

    Polls the DB every second and emits the full run state until status
    is complete or failed. Bounded by a 25-minute wall-clock (Cloud Run
    request timeout is 30 min). EventSourceResponse sends ping comments
    every 15s so idle connections aren't reaped by intermediaries.
    """
    MAX_SECONDS = 25 * 60  # 1500s — leaves headroom below Cloud Run's 30m

    async def event_generator():
        last_hash = None
        elapsed = 0
        # Fidelity is computed in a background task that finishes a few
        # seconds AFTER the run flips to 'complete'. Hold the stream open a
        # bounded grace period past completion so the final 'update' carries
        # the fidelity slice (the persona-consistency badge) — otherwise the
        # client would have to manually refresh to see it.
        grace = 0
        FIDELITY_GRACE_SECONDS = 45
        while elapsed < MAX_SECONDS:
            run = await state.get_run(run_id)
            if run is None:
                yield {"event": "error", "data": json.dumps({"error": "run not found"})}
                return
            payload = run.model_dump_json()
            payload_hash = hash(payload)
            if payload_hash != last_hash:
                yield {"event": "update", "data": payload}
                last_hash = payload_hash
            if run.status == "failed":
                return
            if run.status == "complete":
                if run.fidelity is not None or grace >= FIDELITY_GRACE_SECONDS:
                    return
                grace += 1
            await asyncio.sleep(1)
            elapsed += 1

    # ping=15 emits an SSE comment every 15s so the connection stays
    # warm even when there's no state change (long synthesizer phase etc).
    return EventSourceResponse(event_generator(), ping=15)


@app.get("/api/personas")
async def list_personas(tag: str | None = None) -> list[dict]:
    personas = await state.list_personas(tag=tag)
    return [json.loads(p.model_dump_json()) for p in personas]


# ---------------------------------------------------------------------------
# Image serving (so the frontend can show uploaded variants)
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/image/{which}")
async def get_run_image(run_id: str, which: str):
    if which not in ("a", "b"):
        raise HTTPException(status_code=400, detail="which must be 'a' or 'b'")
    run = await state.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    path = run.variant_a_path if which == "a" else run.variant_b_path
    if not path:
        raise HTTPException(status_code=404, detail="Variant not available for this run")
    return FileResponse(path)


# ---------------------------------------------------------------------------
# Exports for PMs — markdown, plain-language summary, standalone share page
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/summary")
async def get_pm_summary(run_id: str) -> dict:
    """PM-friendly summary: plain language, no technical jargon."""
    run = await state.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return exports.pm_summary(run)


@app.get("/api/runs/{run_id}/export.md", response_class=PlainTextResponse)
async def export_markdown(run_id: str) -> str:
    """Markdown export — paste into Notion / Linear / Jira / Slack."""
    run = await state.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    share_url = f"{CONFIG.frontend_url}/runs/{run_id}"
    return exports.to_markdown(run, share_url=share_url)


@app.get("/share/{run_id}", response_class=HTMLResponse)
async def share_page(run_id: str) -> str:
    """Standalone HTML share page — no frontend build required.

    A PM can send this URL to anyone (Slack, email, PRD) and they get
    a self-contained result page that works on any device.
    """
    run = await state.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return exports.to_share_html(run)


# ---------------------------------------------------------------------------
# A2A protocol — thin adapter over the REST API for Marketplace listing
# ---------------------------------------------------------------------------

@app.get("/.well-known/agent-card.json")
async def agent_card() -> dict:
    """A2A-protocol agent card for Google Cloud Marketplace discovery."""
    return {
        "$schema": "https://a2aprotocol.ai/schemas/agent-card/v1",
        "name": "SimAB — UX Pretest Engine",
        "description": (
            "Simulates how a target audience would respond to two landing page "
            "variants before traffic is spent. Returns weighted winner, "
            "friction themes, segment splits, and trust assessment."
        ),
        "version": "0.1.0",
        "capabilities": {
            "streaming": True,
            "multimodal": True,
            "tools": ["ux_pretest"],
        },
        "endpoints": {
            "base_url": "/a2a/v1",
            "create_task": "POST /tasks",
            "get_task": "GET /tasks/{task_id}",
        },
        "authentication": {"schemes": ["api_key"]},
    }


@app.post("/a2a/v1/tasks")
async def a2a_create_task(payload: dict) -> dict:
    """A2A-style task submission. Inputs are inline base64 image data."""
    import base64

    inputs = payload.get("inputs", {})
    try:
        a_bytes = base64.b64decode(inputs["variant_a_b64"])
        b_bytes = base64.b64decode(inputs["variant_b_b64"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="inputs.variant_a_b64 and inputs.variant_b_b64 are required",
        )

    upload_root = Path(CONFIG.upload_dir)
    suffix = uuid.uuid4().hex[:8]
    a_path = upload_root / f"{suffix}_a.png"
    b_path = upload_root / f"{suffix}_b.png"
    a_path.write_bytes(a_bytes)
    b_path.write_bytes(b_bytes)

    run_id = await state.create_run(
        goal=inputs.get("goal", "convert"),
        audience_raw=inputs.get("audience", ""),
        persona_source="paste",
        variant_a_path=str(a_path),
        variant_b_path=str(b_path),
    )

    # Fire-and-forget
    asyncio.create_task(run_pipeline(run_id))

    return {
        "task_id": run_id,
        "status": "accepted",
        "result_url": f"/a2a/v1/tasks/{run_id}",
    }


@app.get("/a2a/v1/tasks/{task_id}")
async def a2a_get_task(task_id: str) -> dict:
    run = await state.get_run(task_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task_id,
        "status": run.status,
        "result": json.loads(run.synthesis.model_dump_json()) if run.synthesis else None,
        "audit": json.loads(run.audit.model_dump_json()) if run.audit else None,
    }
