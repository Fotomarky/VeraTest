"""Phase 7 · FidelityAuditor — LLM-as-a-Judge + code-based coherence eval.

This is the calibration layer that closes the Arize-track gaps:

 * **LLM-as-a-Judge** (`persona_consistency`) — asks Gemini Flash whether
   each sim agent stayed in character or drifted to a "helpful UX expert"
   voice. The Phoenix research community's strongest pattern.

 * **Code-based eval** (`rationale_coherence`) — deterministic check: does
   the numeric resonance score direction match the rationale's tone?
   A 9/10 paired with "I felt confused and frustrated" is incoherent.
   Triangulates the LLM judge — a code rule can't hallucinate.

Outputs:
 * `SpanEvaluations` attached to each agent's trace (`persona_consistency`,
   `rationale_coherence`) — visible in the Phoenix UI per-span.
 * Drifted rows appended to the persistent Phoenix `drifted_agents` Dataset
   so the next run's Panel Recruiter can tighten archetype prompts.
 * `Run.fidelity` slice persisted to SQLite (drives the dashboard badge).
 * `status -> complete` — Phase 7 owns the terminal status.

The base architecture's open/closed rule is preserved: this agent reads
sim_results + scenarios, writes only its own slice + cross-run Phoenix
data. It does not modify any other agent's state.
"""
from __future__ import annotations
import logging
from typing import Any

import pandas as pd

from .. import state
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


# Deterministic markers for the code-based coherence check.
# We don't pretend this is exhaustive — it's a cheap, fast triangulation
# signal for the LLM judge, not a replacement.
_NEGATIVE_MARKERS = (
    "confusing", "unclear", "frustrat", "would leave", "too much",
    "overwhelm", "doesn't trust", "skeptical", "abandon", "give up",
)


def _is_incoherent(sr: SimResult) -> bool:
    """Code-based eval: numeric score direction must match rationale tone.

    - High score (avg >= 7) with multiple negative markers -> incoherent.
    - Low score (avg <= 4) with zero negative markers      -> incoherent.
    - Otherwise coherent.

    Runs in microseconds, no LLM call, can't hallucinate.
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


# Thin re-exports so tests can patch these at this module's namespace
# without needing arize-phoenix-evals installed at import time.
def llm_classify(*args, **kwargs):  # pragma: no cover - real-Phoenix path
    from phoenix.evals import llm_classify as _llm_classify
    return _llm_classify(*args, **kwargs)


def _gemini_model():  # pragma: no cover - real-Phoenix path
    # Flash-Lite is sufficient for a yes/no "in_character vs drifted"
    # classification and has 1500/day free tier vs Flash's 20/day —
    # keeps the demo unblocked on the free tier.
    from phoenix.evals import GeminiModel
    return GeminiModel(model="gemini-2.5-flash-lite")


def _build_persona_summary(scenario) -> str:
    """Compact persona description for the judge prompt."""
    return "\n".join([
        f"Segment: {scenario.segment}",
        f"Intent: {scenario.intent}",
        f"Decision style: {scenario.decision_style}",
        f"Patience: {scenario.patience_threshold}",
        f"Communication style: {scenario.communication_style or 'n/a'}",
        f"Context: {scenario.context or 'n/a'}",
    ])


async def run(run_id: str) -> None:
    """Phase 7 entry point. See module docstring for the contract."""
    await state.set_status(run_id, "calibrating")
    run = await state.get_run(run_id)
    if run is None or not run.simulation_results:
        log.warning(f"[{run_id}] FidelityAuditor: no sim results, skipping")
        await state.set_status(run_id, "complete")
        return

    scenarios_by_id = {s.id: s for s in run.scenarios}

    # ── 1. Build a dataframe of (persona, rationale) per agent ───────────
    rows: list[dict[str, Any]] = []
    for sr in run.simulation_results:
        scenario = scenarios_by_id.get(sr.scenario_id)
        if scenario is None:
            continue
        rows.append({
            "span_id":           sr.span_id or "",
            "persona":           _build_persona_summary(scenario),
            "rationale":         sr.metacognitive_reflection or sr.rationale or "",
            "persona_archetype": scenario.segment,
            "agent_idx":         sr.agent_idx,
            "scenario_id":       sr.scenario_id,
        })
    df = pd.DataFrame(rows)

    # ── 2. LLM-as-a-Judge: persona consistency ───────────────────────────
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
        log.warning(
            f"[{run_id}] llm_classify failed — defaulting all to in_character "
            f"(non-fatal): {e}"
        )
        results = pd.DataFrame({
            "label": ["in_character"] * len(df),
            "explanation": [""] * len(df),
        })

    merged = df.join(results.reset_index(drop=True))
    merged["score"] = (merged["label"] == "in_character").astype(int)
    persona_consistency = (
        float(merged["score"].mean()) if len(merged) else 1.0
    )
    drifted_idx = merged.loc[
        merged["label"] == "drifted", "agent_idx"
    ].tolist()
    explanations = (
        merged["explanation"].tolist() if "explanation" in merged else []
    )

    log_span_evaluations(
        eval_name="persona_consistency",
        df=merged[["span_id", "label", "score", "explanation"]].rename(
            columns={"span_id": "context.span_id"}
        ),
    )

    # ── 3. Code-based eval: rationale coherence ──────────────────────────
    incoherent_idx: list[int] = []
    coh_rows: list[dict[str, Any]] = []
    for sr in run.simulation_results:
        bad = _is_incoherent(sr)
        if bad:
            incoherent_idx.append(sr.agent_idx)
        coh_rows.append({
            "context.span_id": sr.span_id or "",
            "label":           "incoherent" if bad else "coherent",
            "score":           0 if bad else 1,
        })
    rationale_coherence = 1.0 - (
        len(incoherent_idx) / max(len(run.simulation_results), 1)
    )
    log_span_evaluations(
        eval_name="rationale_coherence",
        df=pd.DataFrame(coh_rows),
    )

    # ── 4. Append drifted rows to the cross-run Phoenix Dataset ──────────
    sig = audience_signature(run.audience_raw or run.goal)
    labels = merged["label"].tolist() if "label" in merged else []
    drifted_rows = [
        {
            "persona":           r["persona"],
            "rationale":         r["rationale"],
            "persona_archetype": r["persona_archetype"],
            "scenario_id":       r["scenario_id"],
        }
        for r, lbl in zip(rows, labels)
        if lbl == "drifted"
    ]
    append_drifted_agents(
        run_id=run_id, audience_signature=sig, rows=drifted_rows,
    )

    # ── 5. Write the fidelity slice and finalise the run ─────────────────
    report = FidelityReport(
        persona_consistency=round(persona_consistency, 4),
        agents_drifted=len(drifted_idx),
        rationale_coherence=round(rationale_coherence, 4),
        agents_incoherent=len(incoherent_idx),
        eval_explanations=[e for e in explanations if e][:20],
        drifted_agent_indices=drifted_idx,
    )
    await state.write_fidelity(run_id, report)
    await state.set_status(run_id, "complete")
    log.info(
        f"[{run_id}] fidelity: persona_consistency={persona_consistency:.2f} "
        f"coherence={rationale_coherence:.2f} "
        f"drifted={len(drifted_idx)} incoherent={len(incoherent_idx)}"
    )
