"""Stigmergy shared state, SQLite-backed.

This is the "pheromone trail" for the multi-agent system. Each agent reads
its relevant slice, appends its output, and exits. There is no orchestrator
passing context between agents — they coordinate by reading/writing here.

Why SQLite: zero setup, file-based, ACID transactions out of the box, no
external service. The aiosqlite async wrapper plus SQLite's built-in
locking gives us our distributed mutex for free.
"""
from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from .config import CONFIG
from .models import (
    Run, Brief, ScenarioCard, SimResult, AuditReport, Synthesis, RunStatus
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    phases_complete TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    goal TEXT NOT NULL,
    audience_raw TEXT NOT NULL DEFAULT '',
    persona_source TEXT NOT NULL DEFAULT 'paste',
    variant_a_path TEXT NOT NULL,
    variant_b_path TEXT NOT NULL,
    brief_json TEXT,
    scenarios_json TEXT NOT NULL DEFAULT '[]',
    agent_allocations_json TEXT NOT NULL DEFAULT '[]',
    audit_json TEXT,
    synthesis_json TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS sim_results (
    run_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    agent_idx INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    written_at TEXT NOT NULL,
    PRIMARY KEY (run_id, scenario_id, agent_idx),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_sim_results_run ON sim_results(run_id);

CREATE TABLE IF NOT EXISTS personas (
    persona_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    segment TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    scenario_json TEXT NOT NULL,
    usage_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


# Single shared connection per process (SQLite handles concurrent access fine
# with WAL mode and the BEGIN IMMEDIATE pattern for writes)
_db: Optional[aiosqlite.Connection] = None
_init_lock = asyncio.Lock()


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        async with _init_lock:
            if _db is None:
                _db = await aiosqlite.connect(CONFIG.db_path)
                await _db.execute("PRAGMA journal_mode=WAL")
                await _db.execute("PRAGMA foreign_keys=ON")
                await _db.executescript(SCHEMA)
                await _db.commit()
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


# ---------------------------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------------------------

async def create_run(
    *,
    goal: str,
    audience_raw: str,
    persona_source: str,
    variant_a_path: str,
    variant_b_path: str,
) -> str:
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute(
        """INSERT INTO runs
           (run_id, status, created_at, updated_at, goal, audience_raw,
            persona_source, variant_a_path, variant_b_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, "pending", now, now, goal, audience_raw,
         persona_source, variant_a_path, variant_b_path),
    )
    await db.commit()
    return run_id


async def get_run(run_id: str) -> Optional[Run]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM runs WHERE run_id = ?", (run_id,)
    ) as cur:
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]

    data = dict(zip(cols, row))

    # Pull sim_results separately
    async with db.execute(
        "SELECT result_json FROM sim_results WHERE run_id = ? ORDER BY agent_idx",
        (run_id,),
    ) as cur:
        sim_rows = await cur.fetchall()

    return Run(
        run_id=data["run_id"],
        status=data["status"],
        phases_complete=json.loads(data["phases_complete"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        goal=data["goal"],
        audience_raw=data["audience_raw"],
        persona_source=data["persona_source"],
        variant_a_path=data["variant_a_path"],
        variant_b_path=data["variant_b_path"],
        brief=Brief.model_validate_json(data["brief_json"]) if data["brief_json"] else None,
        scenarios=[ScenarioCard.model_validate(s) for s in json.loads(data["scenarios_json"])],
        agent_allocations=json.loads(data["agent_allocations_json"]),
        simulation_results=[SimResult.model_validate_json(r[0]) for r in sim_rows],
        audit=AuditReport.model_validate_json(data["audit_json"]) if data["audit_json"] else None,
        synthesis=Synthesis.model_validate_json(data["synthesis_json"]) if data["synthesis_json"] else None,
        error=data["error"],
    )


async def list_runs(limit: int = 50) -> list[Run]:
    db = await get_db()
    async with db.execute(
        "SELECT run_id FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
    ) as cur:
        ids = [row[0] for row in await cur.fetchall()]
    return [r for r in [await get_run(rid) for rid in ids] if r is not None]


# ---------------------------------------------------------------------------
# Agent write operations — each one updates a slice of shared state
# ---------------------------------------------------------------------------

async def set_status(run_id: str, status: RunStatus, error: str | None = None) -> None:
    db = await get_db()
    if error:
        await db.execute(
            "UPDATE runs SET status=?, error=?, updated_at=? WHERE run_id=?",
            (status, error, datetime.now(timezone.utc).isoformat(), run_id),
        )
    else:
        await db.execute(
            "UPDATE runs SET status=?, updated_at=? WHERE run_id=?",
            (status, datetime.now(timezone.utc).isoformat(), run_id),
        )
    await db.commit()


async def write_brief(run_id: str, brief: Brief) -> None:
    db = await get_db()
    await db.execute(
        """UPDATE runs SET brief_json=?, phases_complete=json_insert(phases_complete, '$[#]', ?),
           updated_at=? WHERE run_id=?""",
        (brief.model_dump_json(), "brief", datetime.now(timezone.utc).isoformat(), run_id),
    )
    await db.commit()


async def write_scenarios(
    run_id: str, scenarios: list[ScenarioCard], allocations: list[dict]
) -> None:
    db = await get_db()
    await db.execute(
        """UPDATE runs SET scenarios_json=?, agent_allocations_json=?,
           phases_complete=json_insert(phases_complete, '$[#]', ?),
           updated_at=? WHERE run_id=?""",
        (
            json.dumps([s.model_dump() for s in scenarios]),
            json.dumps(allocations),
            "scenarios",
            datetime.now(timezone.utc).isoformat(),
            run_id,
        ),
    )
    await db.commit()


async def append_sim_result(run_id: str, result: SimResult) -> bool:
    """Idempotent write. Returns False if (run_id, scenario_id, agent_idx)
    already exists — the distributed mutex pattern. This makes the system
    naturally resumable: re-running a partially complete pipeline is safe.
    """
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO sim_results (run_id, scenario_id, agent_idx, result_json, written_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                run_id,
                result.scenario_id,
                result.agent_idx,
                result.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
        return True
    except aiosqlite.IntegrityError:
        # Already written by a duplicate task — that's fine
        return False


async def count_sim_results(run_id: str) -> int:
    db = await get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM sim_results WHERE run_id = ?", (run_id,)
    ) as cur:
        row = await cur.fetchone()
    return row[0] if row else 0


async def write_audit(run_id: str, audit: AuditReport) -> None:
    db = await get_db()
    await db.execute(
        """UPDATE runs SET audit_json=?,
           phases_complete=json_insert(phases_complete, '$[#]', ?),
           updated_at=? WHERE run_id=?""",
        (audit.model_dump_json(), "audit", datetime.now(timezone.utc).isoformat(), run_id),
    )
    await db.commit()


async def write_synthesis(run_id: str, synthesis: Synthesis) -> None:
    db = await get_db()
    await db.execute(
        """UPDATE runs SET synthesis_json=?, status=?,
           phases_complete=json_insert(phases_complete, '$[#]', ?),
           updated_at=? WHERE run_id=?""",
        (
            synthesis.model_dump_json(),
            "complete",
            "synthesis",
            datetime.now(timezone.utc).isoformat(),
            run_id,
        ),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Persona library — for reusing scenarios across runs
# ---------------------------------------------------------------------------

async def save_persona(scenario: ScenarioCard, tags: list[str], workspace_id: str = "default") -> None:
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO personas
           (persona_id, workspace_id, segment, tags, scenario_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            scenario.id,
            workspace_id,
            scenario.segment,
            json.dumps(tags),
            scenario.model_dump_json(),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    await db.commit()


async def list_personas(workspace_id: str = "default", tag: str | None = None) -> list[ScenarioCard]:
    db = await get_db()
    if tag:
        async with db.execute(
            "SELECT scenario_json FROM personas WHERE workspace_id = ? AND tags LIKE ?",
            (workspace_id, f'%"{tag}"%'),
        ) as cur:
            rows = await cur.fetchall()
    else:
        async with db.execute(
            "SELECT scenario_json FROM personas WHERE workspace_id = ?",
            (workspace_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [ScenarioCard.model_validate_json(r[0]) for r in rows]
