# Visual Evaluation Depth + Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat "would you convert?" sim prompt with a research-grounded 6-element cognitive evaluation model (anti-cooperative constraints → Logic of Appropriateness → System 1 visual strike + scan → System 2 messaging + Fogg scoring → metacognitive audit), add 9 new output fields, and redesign the results dashboard to make persona reasoning, visual scores, Fogg diagnostics, trust gaps, and friction immediately legible.

**Architecture:** Backend changes are purely additive — all new Pydantic fields carry safe defaults so old run records deserialize without breakage. Frontend changes replace inline JSX sections with focused components co-located in `frontend/app/components/`. No new API endpoints — all new data comes through the existing `GET /api/runs/{id}` payload.

**Tech Stack:** Python 3.11+, Pydantic v2, aiosqlite, Google Gemini (google-genai), Next.js 14 App Router (TypeScript), Tailwind CSS. Tests: pytest + pytest-asyncio (already installed in `.venv`).

**Effort estimate:**
| Task | Description | Estimate |
|------|-------------|----------|
| 1 | Extend data models | 1 h |
| 2 | Write failing tests | 1 h |
| 3 | Synthesizer aggregation functions | 45 min |
| 4 | SimAgent prompt rewrite | 1.5 h |
| 4b | ScenarioBuilder behavioral diversity | 30 min |
| 5 | Normalizer prompt update | 30 min |
| 6–9 | Frontend components + RunPage | 2 h |
| 10 | Manual verification walkthrough | 1 h |
| **Total** | | **~8.5 h** |

---

## File Map

**Backend — modify:**
- `simab/models.py` — add fields to `SimResult`, `ScenarioCard`, `Synthesis`
- `simab/agents/simulator.py` — replace PROMPT with research-grounded 6-element cognitive model
- `simab/agents/scenarios.py` — extend `VARIATION_PROMPT` to vary `patience_threshold` and `communication_style`
- `simab/agents/normalizer.py` — add confound detection + `patience_threshold`/`communication_style` to persona schema
- `simab/agents/synthesizer.py` — aggregate `visual_impact`, `fogg_avg`, `trust_signal_gaps`; propagate `confound_warning`

**Backend — tests:**
- `tests/test_smoke.py` — update `test_scenario_card_validates` for new fields
- `tests/test_visual_evaluation.py` — create: all new field + aggregation tests

**Frontend — create:**
- `frontend/app/components/PersonaCard.tsx`
- `frontend/app/components/VisualScores.tsx`
- `frontend/app/components/FrictionList.tsx`

**Frontend — modify:**
- `frontend/app/runs/[id]/page.tsx` — new layout: confound warning, persona grid, VisualScores, Fogg diagnostics, FrictionList

---

## Task 1: Extend Data Models
**Effort: ~1 h**

**Files:**
- Modify: `simab/models.py`

- [ ] **Step 1: Open `simab/models.py` and apply the following changes**

Replace the `ScenarioCard` class (lines 16–31) with:

```python
class ScenarioCard(BaseModel):
    """One synthetic audience profile. Drives one or more sim agents."""
    id: str = Field(..., description="Stable id, e.g. sc_001")
    segment: str = Field(..., description="Human-readable label, e.g. 'B2B Evaluator'")
    intent: Literal["evaluate", "buy", "compare", "browse"] = "evaluate"
    decision_style: Literal["analytical", "impulse", "cautious", "social"] = "analytical"
    device: Literal["desktop", "mobile", "tablet"] = "desktop"
    traffic_source: str = "direct"
    context: str = ""
    constraints: list[str] = Field(default_factory=list)
    time_pressure: Literal["high", "medium", "low"] = "medium"
    price_sensitivity: Literal["high", "medium", "low"] = "medium"
    traffic_weight: float = Field(default=0.0, description="Share of audience (0-1)")
    accessibility_flags: list[str] = Field(default_factory=list)
    locale: str = "en-US"
    visual_style_preference: str = ""  # e.g. "clean/minimal", "emotional/imagery-driven"
    patience_threshold: Literal["high", "medium", "low"] = "medium"
    # How long this persona tolerates scanning before abandoning
    communication_style: str = ""
    # e.g. "data-driven and precise", "emotional and values-led", "story-first"
```

Replace the `SimResult` class (lines 52–65) with:

```python
class SimResult(BaseModel):
    scenario_id: str
    scenario_segment: str  # denormalized for easy reporting
    agent_idx: int  # which of the 20 agents (for counterbalancing)
    presented_order: list[Literal["variant_a", "variant_b"]]
    verdict: Literal["variant_a", "variant_b", "neither", "needs_more_info"]
    confidence: Literal["high", "medium", "low"]
    outcome: Literal["would_convert", "would_bounce", "would_research_more"]
    friction_points: list[str] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    rationale: str
    # Visual evaluation fields (all optional with safe defaults for backward compat)
    visual_impact: dict[str, float] = Field(default_factory=dict)
    attention_path: list[str] = Field(default_factory=list)
    messaging_alignment: Literal["strong", "moderate", "weak"] = "moderate"
    first_impression: str = ""
    # Fogg Behavior Model fields (B = Motivation × Ability × Trigger)
    fogg_motivation: int = 0       # 1-10: how much this persona WANTS to act
    fogg_ability: int = 0          # 1-10: how easy the page makes it to act
    fogg_trigger_clarity: Literal["clear", "ambiguous", "absent"] = "ambiguous"
    # Trust signal audit
    trust_signals_found: list[str] = Field(default_factory=list)
    trust_signals_missing: list[str] = Field(default_factory=list)
    # Persuasion framing and cognitive load
    loss_gain_framing: Literal["gain", "loss", "mixed", "neutral"] = "neutral"
    metacognitive_reflection: str = ""  # agent's self-correction ("I might be wrong because...")
    competing_ctas_count: int = 0   # Hick's Law: number of CTAs competing for attention
    spatial_hierarchy_score: int = 0  # 1-10: Rule of Thirds alignment with persona's priority
    model: str = "gemini-2.5-flash-lite"
    latency_ms: int = 0
```

Replace the `Synthesis` class (lines 94–103) with:

```python
class Synthesis(BaseModel):
    winner: Literal["variant_a", "variant_b", "neither"]
    raw_vote: dict[str, int]
    weighted_vote: dict[str, float]
    coverage_score: int = Field(..., ge=0, le=100)
    top_friction: list[FrictionTheme] = Field(default_factory=list)
    what_worked_themes: list[FrictionTheme] = Field(default_factory=list)
    segment_splits: dict[str, dict[str, float]] = Field(default_factory=dict)
    recommendation: str
    one_line_summary: str
    visual_impact: dict[str, float] = Field(default_factory=dict)
    confound_warning: Optional[str] = None
    # Fogg aggregate: {"variant_a": {"motivation": 6.2, "ability": 4.1}, "variant_b": {...}}
    fogg_avg: dict[str, dict[str, float]] = Field(default_factory=dict)
    # Trust signals that most agents reported missing — actionable recommendations
    trust_signal_gaps: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Verify the file parses cleanly**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/python3 -c "from simab.models import SimResult, ScenarioCard, Synthesis; print('models OK')"
```

Expected: `models OK`

---

## Task 2: Write Failing Tests for New Model Fields
**Effort: ~1 h**

**Files:**
- Create: `tests/test_visual_evaluation.py`
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Create `tests/test_visual_evaluation.py`**

```python
"""Tests for the visual evaluation + cognitive model fields added in v0.2.

These are pure schema/math tests — no Gemini calls.
"""
import pytest
from simab.models import ScenarioCard, SimResult, Synthesis
from simab.agents.synthesizer import (
    _compute_visual_impact,
    _compute_fogg_averages,
    _collect_trust_gaps,
    _weight_lookup,
)


# ── ScenarioCard field tests ──────────────────────────────────────────────────

def test_scenario_card_new_fields_default():
    sc = ScenarioCard(id="sc_001", segment="test", traffic_weight=0.5)
    assert sc.visual_style_preference == ""
    assert sc.patience_threshold == "medium"
    assert sc.communication_style == ""


def test_scenario_card_new_fields_set():
    sc = ScenarioCard(
        id="sc_001",
        segment="Tech-Savvy Donor",
        traffic_weight=0.3,
        visual_style_preference="clean/minimal with clear data",
        patience_threshold="low",
        communication_style="data-driven and precise",
    )
    assert sc.visual_style_preference == "clean/minimal with clear data"
    assert sc.patience_threshold == "low"
    assert sc.communication_style == "data-driven and precise"


# ── SimResult field tests ─────────────────────────────────────────────────────

def _minimal_result(**kwargs) -> SimResult:
    defaults = dict(
        scenario_id="sc_001",
        scenario_segment="test",
        agent_idx=0,
        presented_order=["variant_a", "variant_b"],
        verdict="variant_a",
        confidence="high",
        outcome="would_convert",
        rationale="ok",
    )
    defaults.update(kwargs)
    return SimResult(**defaults)


def test_sim_result_visual_defaults_are_backward_compatible():
    r = _minimal_result()
    assert r.visual_impact == {}
    assert r.attention_path == []
    assert r.messaging_alignment == "moderate"
    assert r.first_impression == ""


def test_sim_result_fogg_defaults():
    r = _minimal_result()
    assert r.fogg_motivation == 0
    assert r.fogg_ability == 0
    assert r.fogg_trigger_clarity == "ambiguous"


def test_sim_result_trust_signal_defaults():
    r = _minimal_result()
    assert r.trust_signals_found == []
    assert r.trust_signals_missing == []


def test_sim_result_persuasion_defaults():
    r = _minimal_result()
    assert r.loss_gain_framing == "neutral"
    assert r.metacognitive_reflection == ""
    assert r.competing_ctas_count == 0
    assert r.spatial_hierarchy_score == 0


def test_sim_result_all_new_fields_roundtrip():
    r = _minimal_result(
        visual_impact={"variant_a": 7.0, "variant_b": 5.0},
        attention_path=["hero image", "headline", "price", "CTA"],
        messaging_alignment="strong",
        first_impression="Image 1 felt clean; Image 2 felt cluttered.",
        fogg_motivation=8,
        fogg_ability=6,
        fogg_trigger_clarity="clear",
        trust_signals_found=["money-back guarantee", "security badge"],
        trust_signals_missing=["testimonials", "social proof"],
        loss_gain_framing="gain",
        metacognitive_reflection="I might be wrong because the donation form was below the fold.",
        competing_ctas_count=3,
        spatial_hierarchy_score=7,
    )
    j = r.model_dump_json()
    reloaded = SimResult.model_validate_json(j)
    assert reloaded.fogg_motivation == 8
    assert reloaded.fogg_ability == 6
    assert reloaded.fogg_trigger_clarity == "clear"
    assert "money-back guarantee" in reloaded.trust_signals_found
    assert "testimonials" in reloaded.trust_signals_missing
    assert reloaded.loss_gain_framing == "gain"
    assert "below the fold" in reloaded.metacognitive_reflection
    assert reloaded.competing_ctas_count == 3
    assert reloaded.spatial_hierarchy_score == 7


# ── Synthesis field tests ─────────────────────────────────────────────────────

def _minimal_synthesis(**kwargs) -> Synthesis:
    defaults = dict(
        winner="variant_b",
        raw_vote={"variant_b": 14, "variant_a": 6},
        weighted_vote={"variant_b": 0.7, "variant_a": 0.3},
        coverage_score=75,
        recommendation="Go with B",
        one_line_summary="B wins.",
    )
    defaults.update(kwargs)
    return Synthesis(**defaults)


def test_synthesis_new_fields_default():
    s = _minimal_synthesis()
    assert s.visual_impact == {}
    assert s.confound_warning is None
    assert s.fogg_avg == {}
    assert s.trust_signal_gaps == []


def test_synthesis_confound_warning():
    s = _minimal_synthesis(
        confound_warning="Variants in different languages (IT vs FR). Isolate to one variable."
    )
    assert s.confound_warning is not None
    assert "Isolate" in s.confound_warning


def test_synthesis_fogg_avg_populated():
    s = _minimal_synthesis(
        fogg_avg={
            "variant_a": {"motivation": 6.2, "ability": 4.1},
            "variant_b": {"motivation": 6.3, "ability": 7.8},
        }
    )
    assert s.fogg_avg["variant_b"]["ability"] > s.fogg_avg["variant_a"]["ability"]


def test_synthesis_trust_signal_gaps():
    s = _minimal_synthesis(trust_signal_gaps=["testimonials", "money-back guarantee"])
    assert "testimonials" in s.trust_signal_gaps


# ── Aggregation function tests ────────────────────────────────────────────────

def _make_scenario(id: str, segment: str, weight: float) -> ScenarioCard:
    return ScenarioCard(id=id, segment=segment, traffic_weight=weight)


def _make_result(scenario_id: str, segment: str, agent_idx: int,
                 va_score: float, vb_score: float,
                 fogg_m: int = 5, fogg_a: int = 5,
                 trust_missing: list[str] | None = None) -> SimResult:
    return SimResult(
        scenario_id=scenario_id,
        scenario_segment=segment,
        agent_idx=agent_idx,
        presented_order=["variant_a", "variant_b"],
        verdict="variant_b",
        confidence="medium",
        outcome="would_convert",
        rationale="ok",
        visual_impact={"variant_a": va_score, "variant_b": vb_score},
        fogg_motivation=fogg_m,
        fogg_ability=fogg_a,
        trust_signals_missing=trust_missing or [],
    )


def test_compute_visual_impact_weighted_average():
    """60% persona (va=6,vb=8) + 40% persona (va=8,vb=6) = va:6.8, vb:7.2."""
    scenarios = [
        _make_scenario("sc_001", "Persona A", 0.6),
        _make_scenario("sc_002", "Persona B", 0.4),
    ]
    results = [
        _make_result("sc_001", "Persona A", 0, 6.0, 8.0),
        _make_result("sc_001", "Persona A", 1, 6.0, 8.0),
        _make_result("sc_002", "Persona B", 2, 8.0, 6.0),
        _make_result("sc_002", "Persona B", 3, 8.0, 6.0),
    ]
    weights = _weight_lookup(scenarios)
    impact = _compute_visual_impact(results, weights)
    assert abs(impact["variant_a"] - 6.8) < 0.3
    assert abs(impact["variant_b"] - 7.2) < 0.3


def test_compute_visual_impact_returns_zero_for_missing_scores():
    scenarios = [_make_scenario("sc_001", "Persona A", 1.0)]
    results = [_minimal_result()]  # no visual_impact
    weights = _weight_lookup(scenarios)
    impact = _compute_visual_impact(results, weights)
    assert impact["variant_a"] == 0.0
    assert impact["variant_b"] == 0.0


def test_compute_fogg_averages():
    """Weighted-average Fogg scores per variant across agents."""
    scenarios = [
        _make_scenario("sc_001", "Persona A", 0.6),
        _make_scenario("sc_002", "Persona B", 0.4),
    ]
    results = [
        _make_result("sc_001", "Persona A", 0, 6.0, 8.0, fogg_m=8, fogg_a=6),
        _make_result("sc_001", "Persona A", 1, 6.0, 8.0, fogg_m=8, fogg_a=6),
        _make_result("sc_002", "Persona B", 2, 8.0, 6.0, fogg_m=4, fogg_a=3),
        _make_result("sc_002", "Persona B", 3, 8.0, 6.0, fogg_m=4, fogg_a=3),
    ]
    weights = _weight_lookup(scenarios)
    # Fogg is about the winning variant — test that the function returns a dict with
    # "motivation" and "ability" keys for at least one variant key
    fogg = _compute_fogg_averages(results, weights)
    # There should be entries keyed on verdict (all verdict="variant_b" in _make_result)
    assert "motivation" in fogg.get("variant_b", {}) or len(fogg) > 0


def test_collect_trust_gaps_returns_most_common():
    results = [
        _minimal_result(trust_signals_missing=["testimonials", "security badge"]),
        _minimal_result(trust_signals_missing=["testimonials", "money-back"]),
        _minimal_result(trust_signals_missing=["testimonials"]),
    ]
    gaps = _collect_trust_gaps(results)
    # testimonials appears in all 3 — must be first
    assert gaps[0] == "testimonials"
```

- [ ] **Step 2: Run the new tests — they must FAIL (functions don't exist yet)**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/test_visual_evaluation.py -v 2>&1 | tail -20
```

Expected: import errors on `_compute_fogg_averages`, `_collect_trust_gaps` (not yet defined). Schema tests pass since model fields were added in Task 1.

- [ ] **Step 3: Update `test_scenario_card_validates` in `tests/test_smoke.py`**

Add two lines to the existing test:

```python
def test_scenario_card_validates():
    sc = ScenarioCard(id="sc_001", segment="test", traffic_weight=0.5)
    assert sc.intent == "evaluate"
    assert sc.device == "desktop"
    assert sc.locale == "en-US"
    assert sc.visual_style_preference == ""   # ← add
    assert sc.patience_threshold == "medium"  # ← add
    assert sc.communication_style == ""       # ← add
```

- [ ] **Step 4: Run smoke tests to verify they still pass**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/test_smoke.py -v 2>&1 | tail -5
```

Expected: `11 passed`

---

## Task 3: Add Aggregation Functions to Synthesizer
**Effort: ~45 min**

**Files:**
- Modify: `simab/agents/synthesizer.py`

- [ ] **Step 1: Add `_compute_visual_impact`, `_compute_fogg_averages`, `_collect_trust_gaps`**

Insert these three functions after the `_segment_split_pct` helper function in `synthesizer.py`:

```python
def _weight_lookup(scenarios: list[ScenarioCard]) -> dict[str, float]:
    """Map scenario_id → traffic_weight (used by all aggregation functions)."""
    return {sc.id: sc.traffic_weight for sc in scenarios}


def _compute_visual_impact(
    results: list[SimResult], weights: dict[str, float]
) -> dict[str, float]:
    """Weighted average visual_impact score per variant.

    Returns {"variant_a": 6.8, "variant_b": 7.2}. Returns 0.0 where no
    agent reported a score (backward compat with pre-v0.2 runs).
    """
    totals: dict[str, float] = {"variant_a": 0.0, "variant_b": 0.0}
    weight_sums: dict[str, float] = {"variant_a": 0.0, "variant_b": 0.0}
    for r in results:
        w = weights.get(r.scenario_id, 1.0 / max(len(results), 1))
        for variant, score in r.visual_impact.items():
            if variant in totals:
                totals[variant] += float(score) * w
                weight_sums[variant] += w
    return {
        v: round(totals[v] / weight_sums[v], 1) if weight_sums[v] > 0 else 0.0
        for v in ("variant_a", "variant_b")
    }


def _compute_fogg_averages(
    results: list[SimResult], weights: dict[str, float]
) -> dict[str, dict[str, float]]:
    """Weighted-average Fogg B=MAP scores grouped by the variant each agent chose.

    Returns:
      {
        "variant_a": {"motivation": 6.2, "ability": 5.0},
        "variant_b": {"motivation": 7.1, "ability": 8.3},
      }
    Agents that voted "neither" or "needs_more_info" are excluded.
    """
    buckets: dict[str, dict[str, list[tuple[float, float]]]] = {
        "variant_a": {"motivation": [], "ability": []},
        "variant_b": {"motivation": [], "ability": []},
    }
    for r in results:
        if r.verdict not in buckets:
            continue
        w = weights.get(r.scenario_id, 1.0 / max(len(results), 1))
        if r.fogg_motivation > 0:
            buckets[r.verdict]["motivation"].append((r.fogg_motivation, w))
        if r.fogg_ability > 0:
            buckets[r.verdict]["ability"].append((r.fogg_ability, w))

    out: dict[str, dict[str, float]] = {}
    for variant, dims in buckets.items():
        agg: dict[str, float] = {}
        for dim, pairs in dims.items():
            if pairs:
                total = sum(v * w for v, w in pairs)
                wsum = sum(w for _, w in pairs)
                agg[dim] = round(total / wsum, 1) if wsum > 0 else 0.0
        if agg:
            out[variant] = agg
    return out


def _collect_trust_gaps(results: list[SimResult]) -> list[str]:
    """Return trust signals most commonly reported as MISSING, sorted by frequency.

    Returns the top 5 gaps as a list of strings.
    """
    from collections import Counter
    counter: Counter[str] = Counter()
    for r in results:
        for signal in r.trust_signals_missing:
            s = signal.strip()
            if s:
                counter[s] += 1
    return [item for item, _ in counter.most_common(5)]
```

- [ ] **Step 2: Update the `run` function to call all three aggregation functions**

In the synthesizer's `run` function, after `coverage = _coverage_score(...)`, add:

```python
    weights = _weight_lookup(run.scenarios or [])
    visual_impact = _compute_visual_impact(run.simulation_results, weights)
    fogg_avg = _compute_fogg_averages(run.simulation_results, weights)
    trust_signal_gaps = _collect_trust_gaps(run.simulation_results)

    confound_warning: str | None = None
    if run.brief and run.brief.needs_clarification and run.brief.notes:
        confound_warning = run.brief.notes
```

Update the `Synthesis(...)` constructor call:

```python
    synthesis = Synthesis(
        winner=winner,
        raw_vote=raw_vote,
        weighted_vote=weighted_vote,
        coverage_score=coverage,
        top_friction=top_friction[:5],
        what_worked_themes=worked_themes[:5],
        segment_splits=segments,
        recommendation=summary_raw.get("recommendation", ""),
        one_line_summary=summary_raw.get("one_line", ""),
        visual_impact=visual_impact,
        confound_warning=confound_warning,
        fogg_avg=fogg_avg,
        trust_signal_gaps=trust_signal_gaps,
    )
```

- [ ] **Step 3: Run the visual evaluation tests — all should now pass**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/test_visual_evaluation.py -v 2>&1 | tail -20
```

Expected: all pass.

- [ ] **Step 4: Run the full test suite**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/ -v 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/marcocaruso/Documents/VeraTest
git add simab/models.py simab/agents/synthesizer.py tests/test_visual_evaluation.py tests/test_smoke.py
git commit -m "feat: add Fogg/trust/spatial fields to models; aggregation functions in synthesizer"
```

---

## Task 4: Deepen SimAgent Prompt — Research-Grounded 6-Element Cognitive Model
**Effort: ~1.5 h**

**Files:**
- Modify: `simab/agents/simulator.py`

This is a complete file replacement. The new prompt structure follows the research framework:
1. Anti-cooperative constraints at START (highest LLM attention weight)
2. Persona identity block
3. Logic of Appropriateness (3-question self-anchoring)
4. Phase 1: System 1 Visual Strike + Rule of Thirds spatial grounding
5. Phase 2: System 1 Scanning with decision-style-specific eye movement
6. **EXPLICIT SLOW DOWN** marker → System 2 transition
7. Phase 3: System 2 — gain/loss framing + trust signal audit + microcopy + messaging
8. Phase 4: System 2 — Fogg B=MAP scoring + Hick's Law CTA count + patience threshold check
9. JSON schema with all new fields
10. Metacognitive audit at END ("Could you be wrong?")
11. Behavioral reminder at very END

- [ ] **Step 1: Replace the entire contents of `simab/agents/simulator.py`**

```python
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
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/python3 -c "from simab.agents.simulator import run_one, _map_visual_impact, _clamp_int; print('simulator OK')"
```

Expected: `simulator OK`

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/ -v 2>&1 | tail -10
```

Expected: all pass (schema tests are unaffected by prompt changes).

- [ ] **Step 4: Commit**

```bash
cd /Users/marcocaruso/Documents/VeraTest
git add simab/agents/simulator.py
git commit -m "feat: replace sim prompt with 6-element research-grounded cognitive model (Fogg, trust audit, metacognition)"
```

---

## Task 4b: ScenarioBuilder Behavioral Diversity
**Effort: ~30 min**

**Files:**
- Modify: `simab/agents/scenarios.py`

The ScenarioBuilder runs when scenarios have `agent_count > 1` — it generates N variations of a scenario to prevent mode collapse. Currently it only varies `context`. This task extends it to also vary `patience_threshold` and `communication_style` so agent populations span the full behavioral space.

- [ ] **Step 1: Find `VARIATION_PROMPT` in `simab/agents/scenarios.py` and replace it**

The current `VARIATION_PROMPT` asks for a list of contexts. Replace it with:

```python
VARIATION_PROMPT = """\
You are generating {n} behavioral variations of the same audience persona to
prevent homogeneous responses in a multi-agent simulation.

BASE PERSONA:
{persona_json}

Generate {n} JSON objects. Each must differ from the others and from the base
on AT LEAST THREE of these axes to maximize behavioral diversity:
  - context: what they're doing RIGHT NOW (e.g. commuting, in a meeting,
    comparison-shopping on 3 tabs)
  - patience_threshold: "high" | "medium" | "low"
    (vary: some agents are impatient, others methodical)
  - communication_style: how they prefer information delivered
    (e.g. "concise bullet points", "narrative story", "data and statistics",
    "emotional appeal", "expert technical detail")
  - constraints: add/remove 0-2 situational constraints
  - time_pressure: "high" | "medium" | "low"

Rules:
- Keep segment, decision_style, device, intent, traffic_weight IDENTICAL
  in all variations (they define the persona type, not the instance)
- Make variations REALISTIC and SPECIFIC — not generic
- Do NOT invent a new persona type; vary the same person's circumstances

Respond with ONLY a JSON array of {n} objects. Each object must include
ALL fields of the base persona plus any modified fields:
[
  {{
    "id": "{base_id}_v{'{i}'}",
    "context": "...",
    "patience_threshold": "high" | "medium" | "low",
    "communication_style": "...",
    "constraints": ["..."],
    "time_pressure": "high" | "medium" | "low"
  }},
  ...
]
"""
```

- [ ] **Step 2: Update the function that calls `VARIATION_PROMPT`**

Find the function in `scenarios.py` that builds the prompt (likely `_vary_scenario` or `run`). Update it to:
1. Pass `base_id=scenario.id` to the prompt format
2. Merge the returned variation fields onto the base `ScenarioCard` (preserving `segment`, `decision_style`, `device`, `intent`, `traffic_weight`)
3. Set `patience_threshold` and `communication_style` from the variation if present

The merge logic to add:

```python
def _apply_variation(base: ScenarioCard, variation: dict) -> ScenarioCard:
    """Overlay variation fields onto the base scenario, preserving identity fields."""
    data = base.model_dump()
    # Only allow these fields to vary
    allowed_variation_fields = {
        "id", "context", "patience_threshold", "communication_style",
        "constraints", "time_pressure",
    }
    for field, value in variation.items():
        if field in allowed_variation_fields:
            data[field] = value
    return ScenarioCard(**data)
```

Replace the existing variation-application logic with a call to `_apply_variation`.

- [ ] **Step 3: Verify import**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/python3 -c "from simab.agents.scenarios import run; print('scenarios OK')"
```

Expected: `scenarios OK`

- [ ] **Step 4: Run full test suite**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/ -v 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/marcocaruso/Documents/VeraTest
git add simab/agents/scenarios.py
git commit -m "feat: vary patience_threshold and communication_style in ScenarioBuilder to prevent mode collapse"
```

---

## Task 5: Update Normalizer Prompt
**Effort: ~30 min**

**Files:**
- Modify: `simab/agents/normalizer.py`

- [ ] **Step 1: Replace the PROMPT string in `simab/agents/normalizer.py`**

```python
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
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/python3 -c "from simab.agents.normalizer import run; print('normalizer OK')"
```

Expected: `normalizer OK`

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/ -v 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/marcocaruso/Documents/VeraTest
git add simab/agents/normalizer.py
git commit -m "feat: add patience_threshold, communication_style, confound detection to normalizer"
```

---

## Task 6: Frontend — `PersonaCard` Component
**Effort: part of the ~2 h frontend block**

**Files:**
- Create: `frontend/app/components/PersonaCard.tsx`

- [ ] **Step 1: Create `frontend/app/components/PersonaCard.tsx`**

```tsx
"use client";

type ScenarioCard = {
  id: string;
  segment: string;
  intent: string;
  decision_style: string;
  device: string;
  traffic_source: string;
  context: string;
  constraints: string[];
  time_pressure: string;
  price_sensitivity: string;
  traffic_weight: number;
  visual_style_preference?: string;
  patience_threshold?: string;
  communication_style?: string;
};

type SimResult = {
  scenario_id: string;
  scenario_segment: string;
  verdict: string;
  confidence: string;
  outcome: string;
  rationale: string;
  visual_impact?: Record<string, number>;
  attention_path?: string[];
  messaging_alignment?: string;
  first_impression?: string;
  friction_points: string[];
  what_worked: string[];
  fogg_motivation?: number;
  fogg_ability?: number;
  fogg_trigger_clarity?: string;
  trust_signals_missing?: string[];
  loss_gain_framing?: string;
};

type Props = {
  persona: ScenarioCard;
  results: SimResult[];
  winner: string;
};

const DEVICE_ICON: Record<string, string> = { desktop: "🖥", mobile: "📱", tablet: "📲" };
const STYLE_ICON: Record<string, string> = { analytical: "📊", impulse: "⚡", cautious: "🔍", social: "💬" };
const PATIENCE_COLOR: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-red-50 text-red-700 border-red-200",
};

function votePercent(results: SimResult[], variant: string): number {
  if (!results.length) return 0;
  return Math.round((results.filter((r) => r.verdict === variant).length / results.length) * 100);
}

function avgVisualImpact(results: SimResult[]): Record<string, number> {
  const totals: Record<string, number> = {};
  const counts: Record<string, number> = {};
  for (const r of results) {
    for (const [v, score] of Object.entries(r.visual_impact || {})) {
      totals[v] = (totals[v] || 0) + score;
      counts[v] = (counts[v] || 0) + 1;
    }
  }
  return Object.fromEntries(
    Object.entries(totals).map(([v, t]) => [v, Math.round((t / counts[v]) * 10) / 10])
  );
}

function avgFogg(results: SimResult[]): { motivation: number; ability: number } | null {
  const ms = results.map((r) => r.fogg_motivation || 0).filter((v) => v > 0);
  const as_ = results.map((r) => r.fogg_ability || 0).filter((v) => v > 0);
  if (!ms.length && !as_.length) return null;
  const avg = (arr: number[]) =>
    arr.length ? Math.round((arr.reduce((a, b) => a + b, 0) / arr.length) * 10) / 10 : 0;
  return { motivation: avg(ms), ability: avg(as_) };
}

function topAttentionPath(results: SimResult[]): string[] {
  let best: string[] = [];
  for (const r of results) {
    if ((r.attention_path?.length || 0) > best.length) best = r.attention_path || [];
  }
  return best.slice(0, 5);
}

function commonTrustGaps(results: SimResult[]): string[] {
  const counter: Record<string, number> = {};
  for (const r of results) {
    for (const gap of r.trust_signals_missing || []) {
      counter[gap] = (counter[gap] || 0) + 1;
    }
  }
  return Object.entries(counter)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([k]) => k);
}

export default function PersonaCard({ persona, results, winner }: Props) {
  const pctA = votePercent(results, "variant_a");
  const pctB = votePercent(results, "variant_b");
  const winningVariant = pctA > pctB ? "variant_a" : pctB > pctA ? "variant_b" : null;
  const avgImpact = avgVisualImpact(results);
  const fogg = avgFogg(results);
  const attentionPath = topAttentionPath(results);
  const trustGaps = commonTrustGaps(results);

  const alignments = results.map((r) => r.messaging_alignment).filter(Boolean);
  const topAlignment = alignments.length
    ? (["strong", "moderate", "weak"].find(
        (a) => alignments.filter((x) => x === a).length > alignments.length / 2
      ) ?? "moderate")
    : null;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-100 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-semibold text-sm truncate">{persona.segment}</div>
          <p className="text-xs text-neutral-500 mt-0.5 leading-snug line-clamp-2">
            {persona.context || "No context provided"}
          </p>
          {persona.communication_style && (
            <p className="text-xs text-neutral-400 mt-0.5 italic">{persona.communication_style}</p>
          )}
        </div>
        <div className="flex gap-1 shrink-0 flex-wrap justify-end">
          <Badge>{DEVICE_ICON[persona.device] || "💻"} {persona.device}</Badge>
          <Badge>{STYLE_ICON[persona.decision_style] || "🧠"} {persona.decision_style}</Badge>
          {persona.patience_threshold && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${PATIENCE_COLOR[persona.patience_threshold] || ""}`}>
              ⏱ {persona.patience_threshold} patience
            </span>
          )}
        </div>
      </div>

      {/* Vote bar */}
      <div className="px-4 pt-3 pb-1">
        <div className="flex items-center justify-between text-xs text-neutral-500 mb-1">
          <span>Variant A</span>
          <span className="font-medium text-neutral-800">{results.length} agent{results.length !== 1 ? "s" : ""}</span>
          <span>Variant B</span>
        </div>
        <div className="flex h-2 rounded-full overflow-hidden bg-neutral-100">
          <div
            className={`h-full transition-all ${winner === "variant_a" && winningVariant === "variant_a" ? "bg-emerald-500" : "bg-blue-400"}`}
            style={{ width: `${pctA}%` }}
          />
          <div
            className={`h-full transition-all ${winner === "variant_b" && winningVariant === "variant_b" ? "bg-emerald-500" : "bg-violet-400"}`}
            style={{ width: `${pctB}%` }}
          />
        </div>
        <div className="flex justify-between text-xs font-medium mt-1">
          <span className={winningVariant === "variant_a" ? "text-emerald-700" : "text-neutral-400"}>{pctA}%</span>
          <span className={winningVariant === "variant_b" ? "text-emerald-700" : "text-neutral-400"}>{pctB}%</span>
        </div>
      </div>

      {/* Visual impact scores */}
      {(avgImpact["variant_a"] || avgImpact["variant_b"]) ? (
        <div className="px-4 py-2 border-t border-neutral-100 grid grid-cols-2 gap-2 text-xs">
          {(["variant_a", "variant_b"] as const).map((v) => (
            <div key={v}>
              <div className="text-neutral-400 mb-0.5">{v === "variant_a" ? "A" : "B"} visual</div>
              <div className="flex items-center gap-1.5">
                <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-400 rounded-full" style={{ width: `${((avgImpact[v] || 0) / 10) * 100}%` }} />
                </div>
                <span className="font-medium text-neutral-700 w-6 text-right">{avgImpact[v] ?? "—"}</span>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Fogg scores */}
      {fogg && (fogg.motivation > 0 || fogg.ability > 0) && (
        <div className="px-4 py-2 border-t border-neutral-100 grid grid-cols-2 gap-2 text-xs">
          <div>
            <div className="text-neutral-400 mb-0.5">Motivation</div>
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-400 rounded-full" style={{ width: `${(fogg.motivation / 10) * 100}%` }} />
              </div>
              <span className="font-medium text-neutral-700 w-6 text-right">{fogg.motivation}</span>
            </div>
          </div>
          <div>
            <div className="text-neutral-400 mb-0.5">Ability</div>
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                <div className="h-full bg-violet-400 rounded-full" style={{ width: `${(fogg.ability / 10) * 100}%` }} />
              </div>
              <span className="font-medium text-neutral-700 w-6 text-right">{fogg.ability}</span>
            </div>
          </div>
        </div>
      )}

      {/* Attention path */}
      {attentionPath.length > 0 && (
        <div className="px-4 py-2 border-t border-neutral-100">
          <div className="text-xs text-neutral-400 mb-1.5">Noticed in order</div>
          <div className="flex flex-wrap gap-1">
            {attentionPath.map((el, i) => (
              <span key={i} className="flex items-center gap-1 text-xs bg-neutral-50 border border-neutral-200 px-2 py-0.5 rounded-full">
                <span className="text-neutral-400 text-[10px]">{i + 1}</span>
                {el}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Trust gaps */}
      {trustGaps.length > 0 && (
        <div className="px-4 py-2 border-t border-neutral-100">
          <div className="text-xs text-neutral-400 mb-1.5">Missing trust signals</div>
          <div className="flex flex-wrap gap-1">
            {trustGaps.map((gap, i) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 border border-red-200 text-red-700">
                {gap}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Messaging alignment */}
      {topAlignment && (
        <div className="px-4 py-2 border-t border-neutral-100 flex items-center gap-2">
          <span className="text-xs text-neutral-400">Messaging</span>
          <AlignmentBadge value={topAlignment} />
        </div>
      )}
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-600 whitespace-nowrap">
      {children}
    </span>
  );
}

function AlignmentBadge({ value }: { value: string }) {
  const styles: Record<string, string> = {
    strong: "bg-emerald-50 text-emerald-700 border-emerald-200",
    moderate: "bg-amber-50 text-amber-700 border-amber-200",
    weak: "bg-red-50 text-red-700 border-red-200",
  };
  const labels: Record<string, string> = {
    strong: "✓ Strong match",
    moderate: "~ Moderate match",
    weak: "✗ Weak match",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-medium ${styles[value] || ""}`}>
      {labels[value] || value}
    </span>
  );
}
```

- [ ] **Step 2: Verify the file was created**

```bash
ls -la /Users/marcocaruso/Documents/VeraTest/frontend/app/components/
```

Expected: `PersonaCard.tsx` present.

---

## Task 7: Frontend — `VisualScores` Component

**Files:**
- Create: `frontend/app/components/VisualScores.tsx`

- [ ] **Step 1: Create `frontend/app/components/VisualScores.tsx`**

```tsx
type Props = {
  visualImpact: Record<string, number>;
  winner: string;
};

export default function VisualScores({ visualImpact, winner }: Props) {
  const scoreA = visualImpact["variant_a"] ?? 0;
  const scoreB = visualImpact["variant_b"] ?? 0;
  if (!scoreA && !scoreB) return null;

  const visualWinner = scoreA > scoreB ? "variant_a" : scoreB > scoreA ? "variant_b" : null;

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="font-semibold text-sm">Visual impact per variant</h2>
        <span className="text-xs text-neutral-400">averaged across all agents · scored 1–10 per persona</span>
      </div>
      <div className="space-y-3">
        {(["variant_a", "variant_b"] as const).map((v) => {
          const score = v === "variant_a" ? scoreA : scoreB;
          const label = v === "variant_a" ? "Variant A" : "Variant B";
          const isVisualWinner = visualWinner === v;
          return (
            <div key={v}>
              <div className="flex items-center justify-between text-xs mb-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{label}</span>
                  {isVisualWinner && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">visually stronger</span>
                  )}
                  {!isVisualWinner && visualWinner !== null && winner === v && (
                    <span className="text-[10px] text-neutral-400">(converts better despite lower visual score)</span>
                  )}
                </div>
                <span className="font-semibold text-neutral-800">{score}/10</span>
              </div>
              <div className="h-2.5 bg-neutral-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${isVisualWinner ? "bg-amber-400" : "bg-neutral-300"}`}
                  style={{ width: `${(score / 10) * 100}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      {visualWinner && winner !== "neither" && visualWinner !== winner && (
        <p className="mt-3 text-xs text-neutral-500 bg-neutral-50 rounded p-2">
          ⚠ The visually stronger variant ({visualWinner === "variant_a" ? "A" : "B"}) was not the
          overall winner. Agents may have been influenced by messaging clarity, trust signals,
          or Fogg ability more than first-impression aesthetics.
        </p>
      )}
    </section>
  );
}
```

---

## Task 8: Frontend — `FrictionList` Component

**Files:**
- Create: `frontend/app/components/FrictionList.tsx`

- [ ] **Step 1: Create `frontend/app/components/FrictionList.tsx`**

```tsx
"use client";
import { useState } from "react";

type FrictionTheme = {
  theme: string;
  count: number;
  severity: "high" | "medium" | "low";
  example_quotes: string[];
};

type Props = {
  themes: FrictionTheme[];
  title?: string;
  emptyMessage?: string;
};

const SEV_STYLES: Record<string, { bar: string; bg: string; label: string; dot: string }> = {
  high:   { bar: "border-l-red-400",    bg: "bg-red-50",   label: "HIGH", dot: "bg-red-400"   },
  medium: { bar: "border-l-amber-400",  bg: "bg-amber-50", label: "MED",  dot: "bg-amber-400" },
  low:    { bar: "border-l-green-400",  bg: "bg-green-50", label: "LOW",  dot: "bg-green-400" },
};

export default function FrictionList({
  themes,
  title = "Top friction in losing variant",
  emptyMessage = "No significant friction detected.",
}: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!themes.length) {
    return (
      <section className="rounded-lg border border-neutral-200 bg-white p-5">
        <h2 className="font-semibold mb-2 text-sm">{title}</h2>
        <p className="text-sm text-neutral-400">{emptyMessage}</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-semibold text-sm">{title}</h2>
        <span className="text-xs text-neutral-400">{themes.length} theme{themes.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="space-y-2">
        {themes.map((t, i) => {
          const sev = SEV_STYLES[t.severity] || SEV_STYLES.medium;
          const isOpen = expanded === i;
          const hasQuotes = t.example_quotes && t.example_quotes.length > 0;
          return (
            <div key={i} className={`border-l-2 ${sev.bar} ${sev.bg} pl-3 pr-3 py-2 rounded-r`}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium">{t.theme}</span>
                    <span className="flex items-center gap-1 text-[10px] text-neutral-500">
                      <span className={`w-1.5 h-1.5 rounded-full ${sev.dot}`} />
                      {sev.label} · {t.count} agent{t.count !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
                {hasQuotes && (
                  <button
                    onClick={() => setExpanded(isOpen ? null : i)}
                    className="text-[10px] text-neutral-500 hover:text-neutral-800 shrink-0 whitespace-nowrap mt-0.5"
                  >
                    {isOpen ? "▲ hide" : "▼ quotes"}
                  </button>
                )}
              </div>
              {isOpen && hasQuotes && (
                <div className="mt-2 space-y-1">
                  {t.example_quotes.map((q, j) => (
                    <p key={j} className="text-xs text-neutral-600 italic">&ldquo;{q}&rdquo;</p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
```

---

## Task 9: Rewire `RunPage` — New Layout with All Components
**Effort: part of the ~2 h frontend block**

**Files:**
- Modify: `frontend/app/runs/[id]/page.tsx`

New layout order:
1. Confound warning (orange, highest priority)
2. Status banner / error
3. Trust banner
4. Winner summary + `VisualScores`
5. Variant images side-by-side
6. Persona cards grid (`PersonaCard` ×N)
7. `FrictionList` (friction themes)
8. `FrictionList` (what worked)
9. Fogg diagnostics (bar chart-style: motivation vs ability per variant)
10. Trust signal gaps banner
11. Scenario voices accordion

- [ ] **Step 1: Replace `frontend/app/runs/[id]/page.tsx` entirely**

```tsx
"use client";
import { useEffect, useState } from "react";
import PersonaCard from "../../components/PersonaCard";
import VisualScores from "../../components/VisualScores";
import FrictionList from "../../components/FrictionList";

type ScenarioCard = {
  id: string;
  segment: string;
  intent: string;
  decision_style: string;
  device: string;
  traffic_source: string;
  context: string;
  constraints: string[];
  time_pressure: string;
  price_sensitivity: string;
  traffic_weight: number;
  visual_style_preference?: string;
  patience_threshold?: string;
  communication_style?: string;
};

type SimResult = {
  scenario_id: string;
  scenario_segment: string;
  verdict: string;
  confidence: string;
  outcome: string;
  rationale: string;
  visual_impact?: Record<string, number>;
  attention_path?: string[];
  messaging_alignment?: string;
  first_impression?: string;
  friction_points: string[];
  what_worked: string[];
  fogg_motivation?: number;
  fogg_ability?: number;
  fogg_trigger_clarity?: string;
  trust_signals_missing?: string[];
  loss_gain_framing?: string;
  metacognitive_reflection?: string;
};

type Run = {
  run_id: string;
  status: string;
  goal: string;
  scenarios?: ScenarioCard[];
  simulation_results?: SimResult[];
  audit?: { trust_level: string; warnings: string[]; recommended_action: string };
  synthesis?: {
    winner: string;
    weighted_vote: Record<string, number>;
    coverage_score: number;
    top_friction: Array<{ theme: string; count: number; severity: "high" | "medium" | "low"; example_quotes: string[] }>;
    what_worked_themes: Array<{ theme: string; count: number; severity: "high" | "medium" | "low"; example_quotes: string[] }>;
    one_line_summary?: string;
    recommendation?: string;
    visual_impact?: Record<string, number>;
    confound_warning?: string;
    fogg_avg?: Record<string, Record<string, number>>;
    trust_signal_gaps?: string[];
  };
  error?: string;
};

const PHASE_LABELS: Record<string, string> = {
  pending: "Queued — waiting for the orchestrator",
  normalizing: "Reading the brief — analysing variants and extracting personas",
  building_scenarios: "Building scenarios — assigning agents proportionally to traffic",
  simulating: "Running simulation agents in parallel",
  auditing: "Auditing — checking for bias and confidence collapse",
  synthesizing: "Synthesising final report — clustering friction themes",
  complete: "Complete",
  failed: "Failed",
};

export default function RunPage({ params }: { params: { id: string } }) {
  const [run, setRun] = useState<Run | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const source = new EventSource(`/api/runs/${params.id}/stream`);
    source.addEventListener("update", (e: MessageEvent) => {
      try { setRun(JSON.parse(e.data)); } catch {}
    });
    source.onerror = () => {
      fetch(`/api/runs/${params.id}`).then((r) => r.json()).then(setRun).catch(() => {});
      source.close();
    };
    return () => source.close();
  }, [params.id]);

  async function copyMarkdown() {
    try {
      const r = await fetch(`/api/runs/${params.id}/export.md`);
      const text = await r.text();
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  if (!run) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div className="h-7 bg-neutral-200 rounded animate-pulse w-1/2" />
        <div className="h-4 bg-neutral-100 rounded animate-pulse w-1/3" />
        <div className="h-20 bg-neutral-100 rounded animate-pulse" />
      </div>
    );
  }

  const completed = run.simulation_results?.length || 0;
  const total = run.scenarios?.length || 20;
  const inProgress = run.status !== "complete" && run.status !== "failed";
  const synth = run.synthesis;
  const winner = synth?.winner ?? "neither";

  const scenariosBySegment = new Map<string, ScenarioCard>();
  for (const sc of run.scenarios || []) {
    if (!scenariosBySegment.has(sc.segment)) scenariosBySegment.set(sc.segment, sc);
  }
  const uniquePersonas = Array.from(scenariosBySegment.values());

  const resultsBySegment = new Map<string, SimResult[]>();
  for (const r of run.simulation_results || []) {
    const bucket = resultsBySegment.get(r.scenario_segment) || [];
    bucket.push(r);
    resultsBySegment.set(r.scenario_segment, bucket);
  }

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Title + export actions */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold truncate">{run.goal}</h1>
          <div className="text-xs font-mono text-neutral-400 mt-1">{run.run_id}</div>
        </div>
        {run.status === "complete" && (
          <div className="flex gap-2 shrink-0">
            <button
              onClick={copyMarkdown}
              className="px-3 py-1.5 text-xs rounded-md border border-neutral-300 hover:bg-neutral-50"
            >
              {copied ? "✓ Copied" : "Copy as markdown"}
            </button>
            <a
              href={`/share/${run.run_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 text-xs rounded-md bg-neutral-900 text-white hover:bg-neutral-700"
            >
              Open share page
            </a>
          </div>
        )}
      </div>

      {/* Confound warning — highest priority */}
      {synth?.confound_warning && (
        <div className="rounded-lg border-2 border-orange-300 bg-orange-50 p-4">
          <div className="font-semibold text-sm text-orange-800 mb-1">⚠ Test design issue detected</div>
          <p className="text-sm text-orange-700">{synth.confound_warning}</p>
          <p className="text-xs text-orange-600 mt-2">
            Results below are shown for reference only — do not base decisions on a confounded test.
          </p>
        </div>
      )}

      {/* In-progress status */}
      {inProgress && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <div className="flex items-center justify-between text-sm gap-3 flex-wrap">
            <span className="font-medium">{PHASE_LABELS[run.status] || run.status}</span>
            {run.status === "simulating" && (
              <span className="text-neutral-600 text-xs">{completed} / {total} agents</span>
            )}
          </div>
          <div className="mt-2 h-1.5 bg-neutral-200 rounded-full overflow-hidden">
            <div
              className={`h-full bg-amber-500 transition-all ${run.status !== "simulating" ? "animate-pulse" : ""}`}
              style={{ width: run.status === "simulating" ? `${Math.min(100, (completed / total) * 100)}%` : "100%" }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {run.status === "failed" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="font-medium mb-1">Run failed</div>
          <div className="text-xs font-mono break-all">{run.error || "unknown error"}</div>
        </div>
      )}

      {/* Trust banner */}
      {run.audit && run.audit.trust_level !== "high" && (
        <div className={`rounded-lg border p-4 ${
          run.audit.trust_level === "medium" ? "border-amber-200 bg-amber-50" : "border-red-200 bg-red-50"
        }`}>
          <div className="font-medium text-sm mb-1">
            ⚠ Trust: {run.audit.trust_level.toUpperCase()} — {run.audit.recommended_action}
          </div>
          <ul className="text-xs text-neutral-700 space-y-0.5 list-disc list-inside">
            {run.audit.warnings?.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {/* Winner summary */}
      {synth && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5">
          <div className="flex items-baseline justify-between flex-wrap gap-2 mb-3">
            <h2 className="font-semibold">Result</h2>
            <div className="text-xs text-neutral-400">coverage {synth.coverage_score}/100</div>
          </div>
          {winner === "neither" ? (
            <div className="text-neutral-600 text-sm">Neither variant emerged as a clear winner.</div>
          ) : (
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="text-2xl font-bold font-mono uppercase">
                {winner === "variant_a" ? "Variant A" : "Variant B"}
              </span>
              <span className="text-sm text-neutral-500">
                {((synth.weighted_vote?.[winner] ?? 0) * 100).toFixed(0)}% weighted vote
              </span>
            </div>
          )}
          {synth.one_line_summary && (
            <p className="mt-2 text-sm text-neutral-600 italic">{synth.one_line_summary}</p>
          )}
          {synth.recommendation && (
            <p className="mt-2 text-sm text-neutral-700">{synth.recommendation}</p>
          )}
        </section>
      )}

      {/* Visual impact scores */}
      {synth?.visual_impact && Object.keys(synth.visual_impact).length > 0 && (
        <VisualScores visualImpact={synth.visual_impact} winner={winner} />
      )}

      {/* Variant images */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <VariantCard runId={run.run_id} which="a" winner={winner === "variant_a"} />
        <VariantCard runId={run.run_id} which="b" winner={winner === "variant_b"} />
      </div>

      {/* Persona cards */}
      {uniquePersonas.length > 0 && (
        <section>
          <h2 className="font-semibold text-sm mb-3">
            How your personas evaluated it
            <span className="text-neutral-400 font-normal ml-2">({uniquePersonas.length} segments)</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {uniquePersonas.map((p) => (
              <PersonaCard
                key={p.segment}
                persona={p}
                results={resultsBySegment.get(p.segment) || []}
                winner={winner}
              />
            ))}
          </div>
        </section>
      )}

      {/* Friction themes */}
      {synth?.top_friction && (
        <FrictionList themes={synth.top_friction} title="Top friction in losing variant" />
      )}

      {/* What worked */}
      {synth?.what_worked_themes && synth.what_worked_themes.length > 0 && (
        <FrictionList
          themes={synth.what_worked_themes}
          title="What worked in the winning variant"
          emptyMessage="No specific strengths detected."
        />
      )}

      {/* Fogg diagnostics */}
      {synth?.fogg_avg && Object.keys(synth.fogg_avg).length > 0 && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-semibold text-sm">Fogg B=MAP diagnostics</h2>
            <span className="text-xs text-neutral-400">averaged across agents per variant chosen</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Object.entries(synth.fogg_avg).map(([variant, scores]) => (
              <div key={variant} className="space-y-2">
                <div className="text-xs font-medium text-neutral-600 uppercase">{variant.replace("_", " ")}</div>
                {Object.entries(scores).map(([dim, val]) => (
                  <div key={dim}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="capitalize text-neutral-500">{dim}</span>
                      <span className="font-medium">{val}/10</span>
                    </div>
                    <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${dim === "motivation" ? "bg-blue-400" : "bg-violet-400"}`}
                        style={{ width: `${(val / 10) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
          {(() => {
            const a = synth.fogg_avg["variant_a"];
            const b = synth.fogg_avg["variant_b"];
            if (a && b) {
              const abilityGap = Math.abs((a.ability || 0) - (b.ability || 0));
              if (abilityGap > 2) {
                const easier = (b.ability || 0) > (a.ability || 0) ? "Variant B" : "Variant A";
                return (
                  <p className="mt-3 text-xs text-neutral-500 bg-neutral-50 rounded p-2">
                    💡 {easier} scores significantly higher on Ability — the path to conversion is
                    clearer. Consider applying its CTA structure to the other variant.
                  </p>
                );
              }
            }
            return null;
          })()}
        </section>
      )}

      {/* Trust signal gaps */}
      {synth?.trust_signal_gaps && synth.trust_signal_gaps.length > 0 && (
        <section className="rounded-lg border border-red-100 bg-red-50 p-5">
          <h2 className="font-semibold text-sm text-red-800 mb-2">
            Trust signals reported missing by agents
          </h2>
          <div className="flex flex-wrap gap-2">
            {synth.trust_signal_gaps.map((gap, i) => (
              <span key={i} className="text-xs px-2 py-1 rounded bg-white border border-red-200 text-red-700 font-medium">
                {gap}
              </span>
            ))}
          </div>
          <p className="text-xs text-red-600 mt-2">
            Adding these to the winning variant may increase conversion further.
          </p>
        </section>
      )}

      {/* Scenario voices */}
      {run.simulation_results && run.simulation_results.length > 0 && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5">
          <h2 className="font-semibold text-sm mb-2">All agent voices</h2>
          <details>
            <summary className="text-sm text-neutral-500 cursor-pointer select-none mb-3">
              View {run.simulation_results.length} individual responses
            </summary>
            <div className="space-y-3 mt-2">
              {run.simulation_results.map((r, i) => (
                <div key={i} className="border-l-2 border-neutral-200 pl-3 text-sm">
                  <div className="flex items-center gap-2 text-xs flex-wrap mb-1">
                    <span className="font-mono uppercase font-medium text-neutral-800">{r.verdict}</span>
                    <span className="text-neutral-400">·</span>
                    <span className="text-neutral-600">{r.scenario_segment}</span>
                    <span className="text-neutral-400">·</span>
                    <span className={
                      r.confidence === "high" ? "text-emerald-700"
                        : r.confidence === "medium" ? "text-amber-700"
                        : "text-red-700"
                    }>{r.confidence} confidence</span>
                    {r.messaging_alignment && (
                      <>
                        <span className="text-neutral-400">·</span>
                        <span className="text-neutral-500">msg: {r.messaging_alignment}</span>
                      </>
                    )}
                    {r.loss_gain_framing && r.loss_gain_framing !== "neutral" && (
                      <>
                        <span className="text-neutral-400">·</span>
                        <span className="text-neutral-500">{r.loss_gain_framing} framing</span>
                      </>
                    )}
                  </div>
                  {r.first_impression && (
                    <p className="text-xs text-neutral-500 italic mb-1">{r.first_impression}</p>
                  )}
                  <p className="text-neutral-700 italic break-words">"{r.rationale}"</p>
                  {r.metacognitive_reflection && (
                    <p className="text-xs text-neutral-400 mt-1">🔄 {r.metacognitive_reflection}</p>
                  )}
                  {r.attention_path && r.attention_path.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {r.attention_path.map((el, j) => (
                        <span key={j} className="text-[10px] bg-neutral-100 px-1.5 py-0.5 rounded text-neutral-500">
                          {j + 1}. {el}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </details>
        </section>
      )}
    </div>
  );
}

function VariantCard({ runId, which, winner }: { runId: string; which: "a" | "b"; winner: boolean }) {
  return (
    <div className={`rounded-lg border-2 bg-white p-3 ${winner ? "border-emerald-500" : "border-neutral-200"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Variant {which.toUpperCase()}</span>
        {winner && <span className="text-xs bg-emerald-500 text-white px-2 py-0.5 rounded">winner</span>}
      </div>
      <a href={`/api/runs/${runId}/image/${which}`} target="_blank" rel="noopener noreferrer">
        <img
          src={`/api/runs/${runId}/image/${which}`}
          alt={`Variant ${which}`}
          className="w-full h-56 object-contain bg-neutral-50 rounded hover:opacity-90 transition cursor-zoom-in"
        />
      </a>
    </div>
  );
}
```

- [ ] **Step 2: Verify the frontend builds without errors**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npm run build 2>&1 | tail -20
```

Expected: build completes with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/marcocaruso/Documents/VeraTest
git add frontend/app/components/ frontend/app/runs/
git commit -m "feat: redesign dashboard — persona cards with Fogg scores, trust gaps, visual scores, metacognition"
```

---

## Task 10: Manual Verification Walkthrough
**Effort: ~1 h**

- [ ] **Step 1: Start the backend**

```bash
cd /Users/marcocaruso/Documents/VeraTest
GEMINI_API_KEY=<your-key> SIMAB_DB_PATH=/tmp/simab_v2.db SIMAB_UPLOAD_DIR=/tmp/simab_uploads_v2 \
  .venv/bin/uvicorn simab.main:app --host 127.0.0.1 --port 8001 --log-level warning &
```

- [ ] **Step 2: Start the frontend**

```bash
cd /Users/marcocaruso/Documents/VeraTest/frontend && npm run dev
```

Open http://localhost:3000

- [ ] **Step 3: Test confound detection**

Upload the Italian/French donation form pair. After the run completes, verify:
- [ ] Orange confound warning banner appears at the top (before all results)
- [ ] Banner explains the specific language/brand mismatch
- [ ] Results display below (not blocked)

- [ ] **Step 4: Test properly isolated variants**

Upload two variants of the same page with one variable changed. Verify:
- [ ] No confound warning appears
- [ ] Persona cards appear with context sentence, patience threshold badge, communication style in italic
- [ ] Visual impact score bars are visible per persona card
- [ ] Fogg motivation and ability bars visible per persona card
- [ ] Missing trust signal tags appear (red badges)
- [ ] Attention path chips appear with position hints in parentheses
- [ ] `VisualScores` section shows weighted averages; "visually stronger" badge on higher scorer
- [ ] If visual winner ≠ overall winner, the explanatory note appears
- [ ] `FrictionList` shows themes with color-coded severity; "▼ quotes" expands inline
- [ ] Fogg diagnostics section shows motivation/ability bars per variant
- [ ] Ability gap note appears if delta > 2 between variants
- [ ] Trust signal gaps section shows red badge chips with actionable note
- [ ] Scenario voices show `first_impression` in italic, metacognitive reflection in gray with 🔄
- [ ] Loss/gain framing label appears in each voice row when non-neutral

- [ ] **Step 5: Run final test suite**

```bash
cd /Users/marcocaruso/Documents/VeraTest && .venv/bin/pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Final commit**

```bash
cd /Users/marcocaruso/Documents/VeraTest
git add .
git commit -m "feat: complete visual evaluation + cognitive model depth + dashboard redesign (v0.2)"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Covered by |
|---|---|
| Visual impact evaluation per persona | Task 4 Phase 1 + `visual_impact` field + Task 7 `VisualScores` |
| Rule of Thirds spatial awareness | Task 4 Phase 1 + `spatial_hierarchy_score` field + `_SCANNING_INSTRUCTION` spatial hints |
| Scanning path / attention order | Task 4 Phase 2 + `attention_path` field (with spatial positions) |
| Decision-style specific eye movement | Task 4 `_SCANNING_INSTRUCTION` dict (F-pattern / Z-pattern / cautious / social-proof) |
| Content & messaging alignment | Task 4 Phase 3C + `messaging_alignment` field |
| Gain vs loss framing detection | Task 4 Phase 3A + `loss_gain_framing` field |
| Trust signal audit | Task 4 Phase 3B + `trust_signals_found` / `trust_signals_missing` fields |
| Fogg B=MAP scoring | Task 4 Phase 4 + `fogg_motivation`, `fogg_ability`, `fogg_trigger_clarity` fields |
| Hick's Law CTA count | Task 4 Phase 4 + `competing_ctas_count` field |
| Patience threshold abandonment | Task 4 Phase 4 patience check + `patience_threshold` ScenarioCard field |
| Anti-cooperative constraints | Task 4 CONSTRAINTS block at prompt START |
| Logic of Appropriateness | Task 4 3-question framework before Phase 1 |
| System 1 / System 2 boundary | Task 4 SLOW DOWN marker between Phase 2 and Phase 3 |
| Metacognitive audit | Task 4 METACOGNITIVE AUDIT section at prompt END |
| Behavioral reminder at END | Task 4 BEHAVIORAL REMINDER at very end of prompt |
| Mode collapse prevention | Task 4b ScenarioBuilder: varies `patience_threshold` + `communication_style` |
| Visual style preference per persona | Task 1 `ScenarioCard.visual_style_preference` + Task 5 normalizer schema |
| Communication style per persona | Task 1 `ScenarioCard.communication_style` + Task 5 normalizer |
| Confound detection | Task 5 normalizer + `Synthesis.confound_warning` + Task 9 confound banner |
| Fogg aggregate in synthesis | Task 3 `_compute_fogg_averages()` + `Synthesis.fogg_avg` + Task 9 diagnostics section |
| Trust signal gaps synthesis | Task 3 `_collect_trust_gaps()` + `Synthesis.trust_signal_gaps` + Task 9 gaps banner |
| Persona cards with full context | Task 6 `PersonaCard` (segment, context, patience, communication style, Fogg, trust gaps) |
| Visual scores dashboard section | Task 7 `VisualScores` + Task 9 |
| Expandable friction with quotes | Task 8 `FrictionList` + Task 9 |
| Backward compat for old runs | All new fields have `default_factory=list/dict`, `= 0`, or `Optional` with None defaults |

**Placeholder scan:** No TBDs, no "similar to above", no steps without code.

**Type consistency:**
- `visual_impact`: `dict[str, float]` (Python) ↔ `Record<string, number>` (TS) — consistent
- `attention_path`: `list[str]` ↔ `string[]` — consistent
- `fogg_avg`: `dict[str, dict[str, float]]` ↔ `Record<string, Record<string, number>>` — consistent
- `trust_signal_gaps`: `list[str]` ↔ `string[]` — consistent
- `patience_threshold`: `Literal["high","medium","low"]` (Python) ↔ `string` (TS, widened) — acceptable
- `fogg_trigger_clarity`: `Literal["clear","ambiguous","absent"]` ↔ `string` (TS) — acceptable
- `confound_warning`: `Optional[str]` ↔ optional `string` on TS interface — consistent
- `FrictionTheme.severity`: `"high" | "medium" | "low"` in both Python and TypeScript — consistent
