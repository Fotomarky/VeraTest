"""SimAgent v0.3 — single-variant resonance scoring.

Each agent evaluates ONE landing-page variant (cohort-assigned) from one
persona's perspective. Scores six resonance dimensions 1-10. Position bias is
structurally impossible because no agent ever sees both variants.

Cohort assignment: agent_idx % 2  ->  0 = variant_a cohort, 1 = variant_b cohort.
"""
from __future__ import annotations
import logging
import time
from pathlib import Path

from .. import state
from ..llm import MODEL_FLASH_LITE, generate
from ..models import (
    Cohort, RESONANCE_DIMS, RESONANCE_WEIGHTS, ScenarioCard, SimResult,
)

log = logging.getLogger(__name__)


PROMPT = """\
You are evaluating ONE landing page from the perspective of a specific persona.
You will NOT see any other version. Your job is NOT to predict whether you
will convert — that is unknowable. Your job is to honestly evaluate how well
this page RESONATES with who you are.

PERSONA:
- Segment:                {segment}
- Intent:                 {intent}
- Decision style:         {decision_style}
- Device:                 {device}
- Arrived via:            {traffic_source}
- Patience threshold:     {patience_threshold}
- Communication style:    {communication_style}
- Time pressure:          {time_pressure}
- Price sensitivity:      {price_sensitivity}
- Visual style preference: {visual_style_preference}
- Right now:              {context}
- Hard constraints:       {constraints}

CONVERSION GOAL (what the brand wants you to do):
{goal}

THE PAGE (image attached): evaluate it on six dimensions.

Score each dimension 1–10 and give a one-sentence reason from FIRST person.
Be honest, including where the page fits POORLY for you. Inflation is the enemy
— if a dimension is mediocre, score it 4 or 5, not 7. Do not give 7+ unless
the page genuinely earns it for THIS persona.

1. MOTIVATION — does this page speak to what I, a {segment}, actually want?
   Does the headline/value-prop address my specific intent ({intent})?
2. IDENTITY   — does it speak in my world, vocabulary and register?
   Does it feel made for someone like me, or for a generic visitor?
3. SITUATION  — does it acknowledge MY current context (time pressure: {time_pressure},
   constraints listed above, prior experience)?
4. BELIEFS    — does it match my priors about this category / brand / price?
   Anything here that violates what I'd expect from a serious provider?
5. ABILITY    — does it remove the specific friction I would feel?
   Form length, number of decisions, cognitive load — judge for ME.
6. TRIGGER    — is the next step obvious and right-sized for my
   {decision_style} decision style? Is the CTA clear, unambiguous, present?

Also report:
- friction_points: 2–4 SPECIFIC UI/copy elements that BLOCK me
  (be concrete: "form has 8 fields", not "form is too long")
- what_worked: 2–4 specific elements that FIT me
- trust_signals_found / trust_signals_missing: name the signals
- intent_signal: would_act | would_research | would_leave
- confidence: high | medium | low (your confidence in this evaluation)
- first_impression: one sentence on your gut reaction in the first 2 seconds
- metacognitive_reflection: one sentence — what might bias YOUR read of this page?
- rationale: 2–3 sentences in first person tying the scores together

Respond with ONLY this JSON object (no markdown, no commentary):
{{
  "resonance": {{
    "motivation": <1-10>, "identity": <1-10>, "situation": <1-10>,
    "beliefs": <1-10>, "ability": <1-10>, "trigger": <1-10>
  }},
  "resonance_reasons": {{
    "motivation": "...", "identity": "...", "situation": "...",
    "beliefs": "...", "ability": "...", "trigger": "..."
  }},
  "friction_points": ["..."],
  "what_worked": ["..."],
  "trust_signals_found": ["..."],
  "trust_signals_missing": ["..."],
  "intent_signal": "would_act" | "would_research" | "would_leave",
  "confidence": "high" | "medium" | "low",
  "first_impression": "...",
  "metacognitive_reflection": "...",
  "rationale": "..."
}}
"""


def _clamp_int(value: object, lo: int = 1, hi: int = 10) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return 5  # neutral fallback


def _resonance_overall(resonance: dict[str, int]) -> float:
    """Weighted mean using RESONANCE_WEIGHTS. Missing dims contribute 0 to the weight pool."""
    total_w = 0.0
    weighted_sum = 0.0
    for dim in RESONANCE_DIMS:
        if dim in resonance:
            w = RESONANCE_WEIGHTS.get(dim, 0.0)
            weighted_sum += resonance[dim] * w
            total_w += w
    return round(weighted_sum / total_w, 2) if total_w > 0 else 0.0


def _cohort_for(agent_idx: int, single_screen: bool) -> Cohort:
    if single_screen:
        return "variant_a"
    return "variant_a" if agent_idx % 2 == 0 else "variant_b"


async def run_one(run_id: str, agent_idx: int, scenario: ScenarioCard) -> SimResult:
    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    single_screen = not run.variant_b_path
    cohort = _cohort_for(agent_idx, single_screen)
    image_path = run.variant_a_path if cohort == "variant_a" else run.variant_b_path
    image_bytes = Path(image_path).read_bytes()

    prompt = PROMPT.format(
        segment=scenario.segment,
        intent=scenario.intent,
        decision_style=scenario.decision_style,
        device=scenario.device,
        traffic_source=scenario.traffic_source,
        patience_threshold=scenario.patience_threshold,
        communication_style=scenario.communication_style or "not specified",
        time_pressure=scenario.time_pressure,
        price_sensitivity=scenario.price_sensitivity,
        visual_style_preference=scenario.visual_style_preference or "no strong preference",
        context=scenario.context or "(no specific context)",
        constraints=", ".join(scenario.constraints) or "(none)",
        goal=run.goal,
    )

    # TODO P4: switch to CONFIG.model_simulator (gemini-3-flash-preview / 3.5-flash)
    model = MODEL_FLASH_LITE

    t0 = time.monotonic()
    raw = await generate(
        model=model,
        prompt=prompt,
        images=[image_bytes],
        response_schema={},
        temperature=0.4,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    raw_resonance = raw.get("resonance") or {}
    resonance: dict[str, int] = {}
    for dim in RESONANCE_DIMS:
        if dim in raw_resonance:
            resonance[dim] = _clamp_int(raw_resonance[dim])
        else:
            resonance[dim] = 5  # neutral when LLM omits a dim

    overall = _resonance_overall(resonance)

    intent_signal_raw = raw.get("intent_signal", "would_research")
    if intent_signal_raw not in ("would_act", "would_research", "would_leave"):
        intent_signal_raw = "would_research"

    confidence_raw = raw.get("confidence", "medium")
    if confidence_raw not in ("high", "medium", "low"):
        confidence_raw = "medium"

    result = SimResult(
        scenario_id=scenario.id,
        scenario_segment=scenario.segment,
        agent_idx=agent_idx,
        cohort=cohort,
        resonance=resonance,
        resonance_overall=overall,
        intent_signal=intent_signal_raw,
        confidence=confidence_raw,
        friction_points=raw.get("friction_points", []) or [],
        what_worked=raw.get("what_worked", []) or [],
        rationale=str(raw.get("rationale", ""))[:1000],
        first_impression=str(raw.get("first_impression", ""))[:500],
        trust_signals_found=raw.get("trust_signals_found", []) or [],
        trust_signals_missing=raw.get("trust_signals_missing", []) or [],
        metacognitive_reflection=str(raw.get("metacognitive_reflection", ""))[:500],
        model=model,
        latency_ms=latency_ms,
    )

    written = await state.append_sim_result(run_id, result)
    if not written:
        log.debug(f"[{run_id}] agent {agent_idx} result already exists (idempotent skip)")
    return result
