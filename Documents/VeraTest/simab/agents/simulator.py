"""SimAgent — evaluate variants from one scenario's perspective.

Each agent runs through a research-grounded 6-element cognitive evaluation:
  Anti-cooperative constraints → Logic of Appropriateness → System 1 Visual
  Strike → System 1 Scanning → [SLOW DOWN] → System 2 Messaging + Trust →
  System 2 Fogg Decision → Metacognitive Audit → Behavioral Reminder

Counterbalancing: even-indexed agents see Variant A first, odd-indexed see B.
The agent only sees "Image 1" / "Image 2" — mapped back after to variant names.
"""
from __future__ import annotations
import logging
import time
from pathlib import Path

from .. import state
from ..llm import MODEL_FLASH_LITE, generate
from ..models import ScenarioCard, SimResult

log = logging.getLogger(__name__)


_SCANNING_INSTRUCTION: dict[str, str] = {
    "analytical": (
        "You read in a methodical F-pattern: a horizontal sweep across the top, "
        "then your eye moves down the left edge scanning for headers, data points, "
        "and structural landmarks. You note spatial position — top-left gets your "
        "first attention (Rule of Thirds: ~41% of eye-tracking fixations), then "
        "top-right, then bottom-left."
    ),
    "impulse": (
        "You Z-pattern glance: one diagonal sweep from top-left to bottom-right, "
        "landing on the most visually dominant element or the CTA. Reading is "
        "secondary — you act on visual cues and the top-left anchor first. "
        "Bottom-right is nearly invisible to you."
    ),
    "cautious": (
        "You read carefully, top-to-bottom. Your eye lingers specifically on "
        "trust signals positioned in the top-left (primary anchor) and "
        "bottom-left (secondary anchor): security badges, testimonials, "
        "guarantees, fine print. You don't skip sections."
    ),
    "social": (
        "You hunt for social proof before reading anything else, starting from "
        "the top-left quadrant. Reviews, user counts, logos, endorsements — "
        "if they're not near the top, you may never find them. Only after "
        "finding (or not finding) social validation do you read the main copy."
    ),
}

PROMPT = """\
IMPORTANT — READ THESE CONSTRAINTS BEFORE ANYTHING ELSE:
─────────────────────────────────────────────────────────
You are NOT a helpful assistant. You are NOT trying to evaluate both variants
fairly. You are NOT a UX professional offering balanced critique.

You ARE a specific, flawed, real human being with a precise set of needs,
biases, and blind spots. Your job is to react AUTHENTICALLY — including
ignoring parts of the page, misreading copy, projecting your own assumptions,
and abandoning if you lose patience.

Do NOT say "both variants have merit." Do NOT offer design suggestions.
Do NOT give the benefit of the doubt to a variant that doesn't serve your needs.
If something feels off for you, it IS off.

─────────────────────────────────────────────────────────
YOUR PERSONA — anchor your entire evaluation to this identity
─────────────────────────────────────────────────────────
Segment: {segment}
Visual style preference: {visual_style_preference}
Device: {device}
Arrived via: {traffic_source}
Intent: {intent}
Decision style: {decision_style}
Patience threshold: {patience_threshold}
Communication style: {communication_style}
Time pressure: {time_pressure}
Price sensitivity: {price_sensitivity}
Right now: {context}
Hard constraints: {constraints}

CONVERSION GOAL — the action you're deciding whether to take:
{goal}

─────────────────────────────────────────────────────────
LOGIC OF APPROPRIATENESS — answer these three questions silently before evaluating
─────────────────────────────────────────────────────────
1. "What kind of situation is this?" — Is this a trusted brand, an unknown
   site, a familiar category? Does the visual style signal quality, scam,
   or commodity?
2. "What would someone like me typically do in this situation?" — Not what
   you SHOULD do. What would a {segment} actually do?
3. "What aspect of myself is most relevant right now?" — Which part of your
   persona drives the decision: budget, trust, urgency, aesthetics, social proof?

Keep your answers in mind throughout all phases. They are the lens.

─────────────────────────────────────────────────────────
PHASE 1 · SYSTEM 1 — VISUAL STRIKE (pre-conscious, < 500ms)
─────────────────────────────────────────────────────────
Before reading a single word, react to the RAW VISUAL SIGNAL of each image.

Score VISUAL IMPACT 1–10 SPECIFICALLY for you as a {decision_style} {segment}
on {device} with {visual_style_preference} preferences:
  1 = the visual design actively undermines trust or relevance for me
  5 = neutral
  10 = creates exactly the right emotional/aesthetic context for my decision

Consider: colour palette, imagery, density, whitespace, contrast, emotional
tone, and whether the visual hierarchy places the MOST IMPORTANT information
in the top-left quadrant (where ~41% of eye-tracking fixations land).

Also score SPATIAL HIERARCHY ALIGNMENT 1–10:
  "Does the visual priority map match MY priority as a {segment}?"
  (10 = the thing I care most about is the largest, most prominent, top-left)

─────────────────────────────────────────────────────────
PHASE 2 · SYSTEM 1 — SCANNING (0.5–10 seconds)
─────────────────────────────────────────────────────────
{scanning_instruction}

List the 3–5 specific UI elements you notice IN ORDER for the image you find
more visually compelling. Be specific — not "text" but "campaign headline
copy", not "image" but "photo of smiling donor". Include spatial position:
e.g. "hero image (top-left)", "CTA button (bottom-right)".

If your patience_threshold is "{patience_threshold}" and LOW, ask yourself:
did you find what you needed in the first 2 elements? If not, you would
likely bounce before reading further.

─────────────────────────────────────────────────────────

⟵ SLOW DOWN — SHIFT FROM AUTOMATIC TO DELIBERATE THINKING ⟶

Everything above was instinctive. Now activate careful, analytical reasoning.
You are reading critically, not skimming.

─────────────────────────────────────────────────────────
PHASE 3 · SYSTEM 2 — MESSAGING EVALUATION (10–60 seconds)
─────────────────────────────────────────────────────────

A. GAIN vs LOSS FRAMING — classify which framing the copy uses:
   "gain" = "Get X", "Achieve Y", "Unlock Z"
   "loss" = "Don't miss out", "Act before X expires", "Protect against Y"
   "mixed" = both present
   "neutral" = purely functional, no emotional framing
   As a {segment} with {communication_style} communication style, which
   framing works better for YOU? Does this page use the right one?

B. TRUST SIGNAL AUDIT — as a {decision_style} {segment}, which of these
   trust signals do you ACTIVELY LOOK FOR before converting?
   Check each for PRESENCE in the image you're evaluating:
   - Testimonials or user reviews
   - Social proof (user count, "X people did this", logos of known users)
   - Authority signals (certifications, press mentions, expert endorsement)
   - Security/payment safety indicators
   - Money-back guarantee or risk reversal
   - Transparency (pricing, team, contact info visible)
   List which you FOUND and which you're MISSING. Missing signals you require
   create friction — list them in trust_signals_missing.

C. MESSAGING ALIGNMENT:
   "strong" = feels written for someone exactly like me; uses my vocabulary;
              resolves the core question I arrived with ({intent})
   "moderate" = generic but clear — I can extract what I need
   "weak" = misses my world entirely; wrong tone, register, or doesn't
            answer what I came to learn

─────────────────────────────────────────────────────────
PHASE 4 · SYSTEM 2 — FOGG DECISION MODEL (B = Motivation × Ability × Trigger)
─────────────────────────────────────────────────────────
Score for the image you are leaning toward:

MOTIVATION (1–10): How much do I WANT to take the action after seeing this page?
  Consider: does the headline address my specific intent ({intent})?
  Does the value proposition overcome my price sensitivity ({price_sensitivity})?
  Does the emotional tone match my {communication_style}?

ABILITY (1–10): How EASY does this page make it to act?
  Consider: is the CTA immediately obvious? Is the form short?
  Hick's Law — count how many CTAs are competing for attention.
  Every extra CTA roughly doubles decision time.
  If ability score < 5, list the specific friction in friction_points.

TRIGGER CLARITY: Is the CTA:
  "clear" = one dominant action, labeled exactly as I need
  "ambiguous" = I'm not sure what happens if I click
  "absent" = I cannot find a primary action at all

PATIENCE CHECK: Given your patience_threshold is "{patience_threshold}":
  - "low" patience: if ability < 6 OR competing CTAs > 2 OR trigger is
    "ambiguous"/"absent" → you would bounce. Set outcome to "would_bounce".
  - "medium" patience: if ability < 4 → you bounce. Otherwise research more.
  - "high" patience: you read everything; only bounce if trigger is "absent".

─────────────────────────────────────────────────────────
FINAL VERDICT:
Pick the image that genuinely better serves YOUR GOAL as a {segment} —
or "neither" if both are clearly inadequate for you — or "needs_more_info"
if you cannot decide without content not visible in the screenshot.

─────────────────────────────────────────────────────────
RESPOND WITH ONLY THIS JSON OBJECT (no markdown, no commentary):
─────────────────────────────────────────────────────────
{{
  "verdict": "image_1" | "image_2" | "neither" | "needs_more_info",
  "confidence": "high" | "medium" | "low",
  "outcome": "would_convert" | "would_bounce" | "would_research_more",
  "first_impression": "One sentence gut reaction — Image 1 felt X because Y; Image 2 felt X because Y.",
  "visual_impact": {{"image_1": <1-10>, "image_2": <1-10>}},
  "spatial_hierarchy_score": <1-10 for your preferred image>,
  "attention_path": ["first element (position)", "second (position)", "third (position)", "fourth", "fifth"],
  "messaging_alignment": "strong" | "moderate" | "weak",
  "loss_gain_framing": "gain" | "loss" | "mixed" | "neutral",
  "trust_signals_found": ["signal name", ...],
  "trust_signals_missing": ["signal name", ...],
  "fogg_motivation": <1-10>,
  "fogg_ability": <1-10>,
  "fogg_trigger_clarity": "clear" | "ambiguous" | "absent",
  "competing_ctas_count": <integer>,
  "friction_points": ["specific UI element or copy causing friction"],
  "what_worked": ["specific element in preferred image that helped decision"],
  "rationale": "2-3 sentences in first person explaining what tipped the decision"
}}

─────────────────────────────────────────────────────────
METACOGNITIVE AUDIT — before submitting, ask yourself:
─────────────────────────────────────────────────────────
"Could I be wrong about this verdict?" Consider: am I giving too much weight
to visual style and ignoring content? Am I assuming missing information is
absent rather than below the fold? Am I being influenced by what I think is
"good design" vs. what actually serves MY specific goal?

If yes — adjust your verdict or confidence. Either way, record your
self-correction in the "metacognitive_reflection" field:
  "metacognitive_reflection": "I might be wrong because..."

Add this field to the JSON above.

─────────────────────────────────────────────────────────
BEHAVIORAL REMINDER — you are {segment}
─────────────────────────────────────────────────────────
You arrived via {traffic_source}. You are on {device}.
Your patience threshold is {patience_threshold}.
Your intent is {intent}. Your hard constraints: {constraints}.
React as THIS PERSON — not as a UX professional.
"""


def _map_verdict(raw_verdict: str, presented_order: list[str]) -> str:
    if raw_verdict == "image_1":
        return presented_order[0]
    if raw_verdict == "image_2":
        return presented_order[1]
    return raw_verdict  # "neither" or "needs_more_info" pass through


def _map_visual_impact(
    raw_impact: dict, presented_order: list[str]
) -> dict[str, float]:
    result: dict[str, float] = {}
    for img_key, score in raw_impact.items():
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if img_key == "image_1" and len(presented_order) > 0:
            result[presented_order[0]] = score_f
        elif img_key == "image_2" and len(presented_order) > 1:
            result[presented_order[1]] = score_f
    return result


def _clamp_int(value: object, lo: int = 0, hi: int = 10) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return 0


async def run_one(run_id: str, agent_idx: int, scenario: ScenarioCard) -> SimResult:
    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    img_a = Path(run.variant_a_path).read_bytes()
    img_b = Path(run.variant_b_path).read_bytes()

    if agent_idx % 2 == 0:
        presented_order = ["variant_a", "variant_b"]
        images = [img_a, img_b]
    else:
        presented_order = ["variant_b", "variant_a"]
        images = [img_b, img_a]

    scanning_instruction = _SCANNING_INSTRUCTION.get(
        scenario.decision_style, _SCANNING_INSTRUCTION["analytical"]
    )

    prompt = PROMPT.format(
        segment=scenario.segment,
        visual_style_preference=scenario.visual_style_preference or "no strong preference",
        device=scenario.device,
        traffic_source=scenario.traffic_source,
        intent=scenario.intent,
        decision_style=scenario.decision_style,
        patience_threshold=scenario.patience_threshold,
        communication_style=scenario.communication_style or "not specified",
        time_pressure=scenario.time_pressure,
        price_sensitivity=scenario.price_sensitivity,
        context=scenario.context,
        constraints=", ".join(scenario.constraints) or "(none)",
        goal=run.goal,
        scanning_instruction=scanning_instruction,
    )

    t0 = time.monotonic()
    raw = await generate(
        model=MODEL_FLASH_LITE,
        prompt=prompt,
        images=images,
        response_schema={},
        temperature=0.3,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    raw_verdict = raw.get("verdict", "needs_more_info")
    mapped_verdict = _map_verdict(raw_verdict, presented_order)

    raw_visual = raw.get("visual_impact") or {}
    visual_impact = _map_visual_impact(raw_visual, presented_order)

    messaging_raw = raw.get("messaging_alignment", "moderate")
    if messaging_raw not in ("strong", "moderate", "weak"):
        messaging_raw = "moderate"

    framing_raw = raw.get("loss_gain_framing", "neutral")
    if framing_raw not in ("gain", "loss", "mixed", "neutral"):
        framing_raw = "neutral"

    trigger_raw = raw.get("fogg_trigger_clarity", "ambiguous")
    if trigger_raw not in ("clear", "ambiguous", "absent"):
        trigger_raw = "ambiguous"

    result = SimResult(
        scenario_id=scenario.id,
        scenario_segment=scenario.segment,
        agent_idx=agent_idx,
        presented_order=presented_order,
        verdict=mapped_verdict,
        confidence=raw.get("confidence", "low"),
        outcome=raw.get("outcome", "would_bounce"),
        friction_points=raw.get("friction_points", []) or [],
        what_worked=raw.get("what_worked", []) or [],
        rationale=str(raw.get("rationale", ""))[:1000],
        visual_impact=visual_impact,
        attention_path=(raw.get("attention_path") or [])[:7],
        messaging_alignment=messaging_raw,
        first_impression=str(raw.get("first_impression", ""))[:500],
        fogg_motivation=_clamp_int(raw.get("fogg_motivation", 0)),
        fogg_ability=_clamp_int(raw.get("fogg_ability", 0)),
        fogg_trigger_clarity=trigger_raw,
        trust_signals_found=raw.get("trust_signals_found", []) or [],
        trust_signals_missing=raw.get("trust_signals_missing", []) or [],
        loss_gain_framing=framing_raw,
        metacognitive_reflection=str(raw.get("metacognitive_reflection", ""))[:500],
        competing_ctas_count=_clamp_int(raw.get("competing_ctas_count", 0), lo=0, hi=20),
        spatial_hierarchy_score=_clamp_int(raw.get("spatial_hierarchy_score", 0)),
        model=MODEL_FLASH_LITE,
        latency_ms=latency_ms,
    )

    written = await state.append_sim_result(run_id, result)
    if not written:
        log.debug(f"[{run_id}] agent {agent_idx} result already exists (idempotent skip)")
    return result