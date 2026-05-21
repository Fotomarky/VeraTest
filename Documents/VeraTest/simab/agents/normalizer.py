"""BriefNormalizer — the universal input ingester.

Takes raw paste input (free text, JSON, CSV, or campaign brief) plus the
two variant images and the goal, and outputs a structured Brief with
extracted personas. The LLM handles format detection so we don't have
branching code per input shape.
"""
from __future__ import annotations
import logging
from pathlib import Path

from .. import state
from ..llm import MODEL_FLASH, generate
from ..models import Brief, ScenarioCard

log = logging.getLogger(__name__)


PROMPT = """\
You are a UX research assistant analyzing a landing page A/B test.

CONVERSION GOAL: {goal}

AUDIENCE INPUT (could be JSON, CSV, free text, campaign brief, or empty):
---
{audience_raw}
---

You will receive two landing page images: VARIANT A first, then VARIANT B.

Your task: produce a structured brief. Extract or infer:

1. variant_a_summary, variant_b_summary — 1-sentence each describing what
   each page communicates (offer, audience signals, primary CTA).

2. key_differences — 3-5 observable differences between A and B.

3. inferred_personas — array of 3-7 persona objects. Rules:
   - If audience input contains structured persona data, preserve and normalize it.
   - If audience input is free text or a brief, extract the segments.
   - If audience input is empty, derive 5 plausible personas from what
     the page visuals suggest about the target audience.
   - Each persona must include ALL of:
     * segment (string label)
     * intent: "evaluate" | "buy" | "compare" | "browse"
     * decision_style: "analytical" | "impulse" | "cautious" | "social"
     * device: "desktop" | "mobile" | "tablet"
     * traffic_source (string)
     * context: one sentence describing their current situation
     * constraints: list of strings (0-3 situational constraints)
     * time_pressure: "high" | "medium" | "low"
     * price_sensitivity: "high" | "medium" | "low"
     * traffic_weight (0-1, all personas must sum to ~1.0)
     * visual_style_preference: one of "clean/minimal", "emotional/imagery-driven",
       "information-dense", "trust-signal-focused", "social-proof-driven"
     * patience_threshold: "high" | "medium" | "low"
       ("low" = bounces within 5 seconds if key info not immediately visible;
        "medium" = reads main fold; "high" = reads the whole page)
     * communication_style: how this persona prefers information delivered.
       Examples: "concise bullet points", "emotional narrative", "data and
       statistics", "expert technical detail", "social proof and stories"
     * accessibility_flags: [] (empty unless obvious from audience input)
     * locale: e.g. "en-US"

4. test_type — "pre_release" by default.

5. needs_clarification — set TRUE if ANY of these apply:
   - The two variants are in DIFFERENT LANGUAGES (results will measure
     language comprehension, not design — uninterpretable).
   - The variants have DIFFERENT BRAND NAMES or logos.
   - There are more than 3 fundamental simultaneous differences (language +
     brand + layout) — the test is confounded and no variable can be isolated.
   Default: false.

6. notes — if needs_clarification is true, write:
   "Variants appear to be [X]. This means the test measures [Y] rather than
   a single design variable. To get interpretable results, isolate to one
   variable: [specific suggestion]."
   If needs_clarification is false, leave notes as "".

Respond with ONLY a JSON object:
{{
  "conversion_goal": "...",
  "variant_a_summary": "...",
  "variant_b_summary": "...",
  "key_differences": ["...", "..."],
  "test_type": "pre_release",
  "inferred_personas": [
    {{
      "id": "sc_001",
      "segment": "...",
      "intent": "evaluate",
      "decision_style": "analytical",
      "device": "desktop",
      "traffic_source": "...",
      "context": "...",
      "constraints": ["..."],
      "time_pressure": "medium",
      "price_sensitivity": "medium",
      "traffic_weight": 0.30,
      "visual_style_preference": "clean/minimal",
      "patience_threshold": "medium",
      "communication_style": "concise bullet points",
      "accessibility_flags": [],
      "locale": "en-US"
    }}
  ],
  "needs_clarification": false,
  "notes": ""
}}
"""


async def run(run_id: str) -> Brief:
    """Read inputs from shared state, write brief back."""
    run = await state.get_run(run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found")

    await state.set_status(run_id, "normalizing")

    # Load images from disk
    img_a = Path(run.variant_a_path).read_bytes()
    img_b = Path(run.variant_b_path).read_bytes()

    prompt = PROMPT.format(goal=run.goal, audience_raw=run.audience_raw or "(empty)")

    raw = await generate(
        model=MODEL_FLASH,
        prompt=prompt,
        images=[img_a, img_b],
        response_schema={},
        temperature=0.2,
    )

    # Validate + normalize via Pydantic
    brief = Brief.model_validate(raw)

    # Renumber persona IDs deterministically
    for i, p in enumerate(brief.inferred_personas):
        p.id = f"sc_{i+1:03d}"

    await state.write_brief(run_id, brief)
    log.info(f"[{run_id}] brief_normalizer: extracted {len(brief.inferred_personas)} personas")
    return brief
