"""Narrative agents — comparative reasoning without position bias.

Three agents, each engineered to avoid the rationalization trap that the
v0.2 forced-choice simulator fell into:

1. structural_diff   — both images, no winner judgment, factual list of
                       observable differences.
2. symmetric_hypothesis — both images, forced 3-pro + 3-con per variant
                       (the symmetry constraint kills one-sided
                       rationalization).
3. cohort_narrative  — operates on cohort scores + themes + persona splits,
                       NEVER on raw images. Position bias is impossible
                       because the agent never sees a design at all.

The three are independent and run in parallel from the pipeline.
"""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path

from .. import state
from ..llm import MODEL_FLASH, generate

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

STRUCTURAL_DIFF_PROMPT = """\
You are observing two landing page designs side by side.

Your ONLY job: describe what is observably DIFFERENT between them.
Do NOT evaluate which is better. Do NOT recommend. Do NOT speculate on
user behavior. Just describe the differences a careful observer would see.

Both images are attached. Variant A first, Variant B second.

List 5–10 specific factual differences across categories such as: layout,
copy, imagery, form structure, CTA placement, color palette, density, and
trust-signal presence.

Be CONCRETE. Bad: "form is different". Good: "Variant A has a 5-field form
in the right column; Variant B has an 8-field form spanning the full width".

Respond with ONLY:
{"differences": ["...", "...", "..."]}
"""

SYMMETRIC_HYPOTHESIS_PROMPT = """\
You are doing balanced hypothesis generation about two landing page designs.

For EACH variant, write EXACTLY 3 reasons the design might perform better
for some users AND EXACTLY 3 reasons it might perform worse. The 3+3
symmetry is REQUIRED — do not give one variant more pros than the other.

You are NOT picking a winner. The point is to surface tradeoffs both ways.

Both images attached. Variant A first, Variant B second.

Respond with ONLY:
{
  "pros": {
    "variant_a": ["...", "...", "..."],
    "variant_b": ["...", "...", "..."]
  },
  "cons": {
    "variant_a": ["...", "...", "..."],
    "variant_b": ["...", "...", "..."]
  }
}
"""

COHORT_NARRATIVE_PROMPT = """\
You are writing the analysis section of a synthetic UX pretest report.
Use ONLY the aggregated cohort data below — do NOT speculate beyond it.
You are NOT looking at the images.

DIRECTIONAL WINNER:  {winner}
GAP SIGNIFICANCE:    {significance}
RESONANCE GAP:       {gap:+.2f}  (variant_b minus variant_a, 1-10 scale)
COHORT OVERALL:      variant_a = {a_overall:.2f}, variant_b = {b_overall:.2f}

Per-cohort per-dimension resonance:
{cohort_table}

Per-persona resonance overall:
{persona_table}

Top friction themes (in the losing or both cohorts):
{friction_themes}

What worked themes:
{worked_themes}

Trust signals commonly reported as missing:
{trust_gaps}

Write a 2-3 paragraph PM-facing analysis:
1. Open with the directional finding. Use the word "resonance" — NOT
   "conversion" or "lift". Frame the significance honestly (tie / weak /
   moderate / strong).
2. Identify WHICH dimension or persona segment drove the gap most clearly.
   Cite specific numbers.
3. Close with the single most actionable insight — what to fix or test next.

Avoid:
- Predicting conversion rates or percentages
- Generic UX advice not grounded in the data above
- More than 3 short paragraphs
- Headings, markdown, or JSON — plain prose only.

Respond with the narrative text directly.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Individual agents
# ─────────────────────────────────────────────────────────────────────────────

async def structural_diff(run_id: str) -> list[str]:
    """Factual differences only. No winner judgment."""
    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")
    img_a = Path(run.variant_a_path).read_bytes()
    img_b = Path(run.variant_b_path).read_bytes()
    raw = await generate(
        model=MODEL_FLASH,
        prompt=STRUCTURAL_DIFF_PROMPT,
        images=[img_a, img_b],
        response_schema={},
        temperature=0.2,
    )
    diffs = raw.get("differences", []) if isinstance(raw, dict) else []
    return [d for d in diffs if isinstance(d, str) and d.strip()][:10]


async def symmetric_hypothesis(
    run_id: str,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Returns (pros, cons) per variant — each is a 3-item list per variant."""
    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")
    img_a = Path(run.variant_a_path).read_bytes()
    img_b = Path(run.variant_b_path).read_bytes()
    raw = await generate(
        model=MODEL_FLASH,
        prompt=SYMMETRIC_HYPOTHESIS_PROMPT,
        images=[img_a, img_b],
        response_schema={},
        temperature=0.4,
    )
    pros_raw = raw.get("pros", {}) if isinstance(raw, dict) else {}
    cons_raw = raw.get("cons", {}) if isinstance(raw, dict) else {}

    def _clean(d: dict) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {"variant_a": [], "variant_b": []}
        for v in ("variant_a", "variant_b"):
            items = d.get(v) or []
            out[v] = [x for x in items if isinstance(x, str) and x.strip()][:3]
        return out

    return _clean(pros_raw), _clean(cons_raw)


def _format_cohort_table(cohort_res: dict[str, dict[str, float]]) -> str:
    """Compact text table for the narrative prompt."""
    if not cohort_res:
        return "(no cohort data)"
    dims = list(next(iter(cohort_res.values())).keys())
    lines = ["  Dimension       " + "  ".join(f"{c:>10}" for c in cohort_res.keys())]
    for dim in dims:
        scores = "  ".join(f"{cohort_res[c].get(dim, 0):>10.2f}" for c in cohort_res.keys())
        lines.append(f"  {dim:<14}  {scores}")
    return "\n".join(lines)


def _format_persona_table(per_persona: dict[str, dict[str, dict[str, float]]],
                          weights: dict[str, float]) -> str:
    """Per-persona resonance_overall computed from per-dim means + weights."""
    if not per_persona:
        return "(no persona data)"
    lines = ["  Persona                                variant_a  variant_b"]
    for segment, by_cohort in per_persona.items():
        a_overall = _weighted_mean(by_cohort.get("variant_a", {}), weights)
        b_overall = _weighted_mean(by_cohort.get("variant_b", {}), weights)
        seg_label = segment[:38]
        lines.append(f"  {seg_label:<38}  {a_overall:>9.2f}  {b_overall:>9.2f}")
    return "\n".join(lines)


def _weighted_mean(dim_scores: dict[str, float], weights: dict[str, float]) -> float:
    if not dim_scores:
        return 0.0
    total_w = sum(weights.get(d, 0) for d in dim_scores)
    if total_w == 0:
        return 0.0
    return sum(dim_scores[d] * weights.get(d, 0) for d in dim_scores) / total_w


async def cohort_narrative(run_id: str) -> str:
    """Multi-paragraph PM narrative from cohort data. NEVER sees images."""
    run = await state.get_run(run_id)
    if run is None or run.synthesis is None:
        raise ValueError(f"Run {run_id} not ready for narrative")

    from ..models import RESONANCE_WEIGHTS

    synth = run.synthesis
    friction_block = "\n".join(
        f"  - {t.theme} (mentioned {t.count} times, severity {t.severity})"
        for t in synth.top_friction[:5]
    ) or "  (none)"
    worked_block = "\n".join(
        f"  - {t.theme} (mentioned {t.count} times)"
        for t in synth.what_worked_themes[:5]
    ) or "  (none)"
    trust_block = ", ".join(synth.trust_signal_gaps[:5]) or "(none)"

    raw = await generate(
        model=MODEL_FLASH,
        prompt=COHORT_NARRATIVE_PROMPT.format(
            winner=synth.directional_winner,
            significance=synth.gap_significance,
            gap=synth.resonance_gap,
            a_overall=synth.cohort_resonance_overall.get("variant_a", 0.0),
            b_overall=synth.cohort_resonance_overall.get("variant_b", 0.0),
            cohort_table=_format_cohort_table(synth.cohort_resonance),
            persona_table=_format_persona_table(synth.per_persona_resonance, RESONANCE_WEIGHTS),
            friction_themes=friction_block,
            worked_themes=worked_block,
            trust_gaps=trust_block,
        ),
        temperature=0.5,
    )
    return str(raw).strip() if not isinstance(raw, dict) else str(raw.get("narrative", "")).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator — pipeline calls this once after synthesizer
# ─────────────────────────────────────────────────────────────────────────────

async def run(run_id: str) -> None:
    """Run all three narrative agents in parallel and merge into Synthesis."""
    await state.set_status(run_id, "synthesizing")  # remain in this phase

    diff_task = structural_diff(run_id)
    hyp_task = symmetric_hypothesis(run_id)
    narr_task = cohort_narrative(run_id)

    diff_result, (pros, cons), narrative = await asyncio.gather(
        diff_task, hyp_task, narr_task,
        return_exceptions=False,
    )

    # Augment the existing synthesis (set by synthesizer phase) and write back.
    current = await state.get_run(run_id)
    if current is None or current.synthesis is None:
        raise ValueError(f"Run {run_id} has no synthesis to augment")
    syn = current.synthesis
    syn.structural_diff = diff_result
    syn.hypothesis_pros = pros
    syn.hypothesis_cons = cons
    syn.narrative = narrative
    await state.write_synthesis(run_id, syn)
    log.info(
        f"[{run_id}] narrative: diff={len(diff_result)} "
        f"pros={sum(len(v) for v in pros.values())} "
        f"cons={sum(len(v) for v in cons.values())} "
        f"narr_chars={len(narrative)}"
    )
