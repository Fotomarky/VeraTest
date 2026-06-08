"""All Pydantic schemas for SimAB.

Single source of truth for run state, scenario cards, simulation results,
audit findings, and API request/response shapes.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Scenario card — the "persona" with behavioural and contextual fields
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# AudiencePreset — structured chip input from the v0.3 /new page
# ---------------------------------------------------------------------------

class AudiencePreset(BaseModel):
    """Structured audience input from the chip selector UX.

    All fields are optional multi-select arrays. When empty, the normalizer
    falls back to either audience_raw text or pure visual inference.
    """
    age_ranges: list[str] = Field(default_factory=list)
    roles:      list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    interests:  list[str] = Field(default_factory=list)
    behaviors:  list[str] = Field(default_factory=list)
    devices:    list[str] = Field(default_factory=list)
    notes: str = ""

    def is_empty(self) -> bool:
        return not any([
            self.age_ranges, self.roles, self.industries,
            self.interests, self.behaviors, self.devices, self.notes,
        ])


# ---------------------------------------------------------------------------
# Brief — output of the BriefNormalizer agent
# ---------------------------------------------------------------------------

class Brief(BaseModel):
    conversion_goal: str
    variant_a_summary: str
    variant_b_summary: str = ""  # empty for single-screen runs
    key_differences: list[str] = Field(default_factory=list)
    test_type: Literal["pre_release", "post_release"] = "pre_release"
    inferred_personas: list[ScenarioCard] = Field(default_factory=list)
    needs_clarification: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Resonance — the v0.3 evaluation primitive
# ---------------------------------------------------------------------------

Cohort = Literal["variant_a", "variant_b"]

ResonanceDim = Literal[
    "motivation",  # Fogg M — does the page address what this persona wants?
    "identity",    # does it speak in their vocabulary / world / register?
    "situation",   # does it acknowledge current context (time, prior experience)?
    "beliefs",     # does it match priors about category / brand / price?
    "ability",     # Fogg A — does it remove their specific friction?
    "trigger",     # Fogg T — is the next step obvious and right-sized?
]

RESONANCE_DIMS: tuple[str, ...] = (
    "motivation", "identity", "situation", "beliefs", "ability", "trigger",
)

# Default weights used to collapse the 6-dim vector into resonance_overall.
# v0.3 keeps a single set for all personas; per-archetype weights deferred to v0.4.
RESONANCE_WEIGHTS: dict[str, float] = {
    "motivation": 0.25,
    "identity":   0.15,
    "situation":  0.15,
    "beliefs":    0.15,
    "ability":    0.15,
    "trigger":    0.15,
}


# ---------------------------------------------------------------------------
# Simulation result — one sim agent's output
# ---------------------------------------------------------------------------

class SimResult(BaseModel):
    scenario_id: str
    scenario_segment: str            # denormalized for easy reporting
    agent_idx: int                   # which of the N agents (for cohort split)
    cohort: Cohort                   # which variant this agent evaluated
    resonance: dict[str, int] = Field(
        default_factory=dict,
        description="Per-dimension 1-10 score; keys are ResonanceDim values",
    )
    resonance_overall: float = 0.0   # weighted mean of resonance dims, 1.0-10.0
    intent_signal: Literal["would_act", "would_research", "would_leave"] = "would_research"
    confidence: Literal["high", "medium", "low"] = "medium"
    friction_points: list[str] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    rationale: str = ""
    first_impression: str = ""
    trust_signals_found: list[str] = Field(default_factory=list)
    trust_signals_missing: list[str] = Field(default_factory=list)
    metacognitive_reflection: str = ""  # agent's self-correction
    model: str = "gemini-3-flash-preview"
    latency_ms: int = 0
    span_id: Optional[str] = None
    # Phoenix span id (16-hex) captured at trace time so the FidelityAuditor
    # can attach Span Evaluations back to the exact agent invocation.


# ---------------------------------------------------------------------------
# Audit — output of the BiasAuditor agent
# ---------------------------------------------------------------------------

class AuditReport(BaseModel):
    trust_level: Literal["high", "medium", "low"]
    confidence_collapse: bool = False
    low_confidence_rate: float = 0.0
    avg_rationale_coherence: float = 1.0  # 0-1
    segment_divergence: dict[str, dict[str, int]] = Field(default_factory=dict)
    # Cohort-balance checks replace v0.2 order-bias checks.
    cohort_balance: dict[str, int] = Field(
        default_factory=dict,
        description="{variant_a: 10, variant_b: 10}",
    )
    cohort_persona_balance: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="{segment: {variant_a: 3, variant_b: 2}}",
    )
    per_dim_variance: dict[str, float] = Field(
        default_factory=dict,
        description="Variance of resonance scores per dim across all agents — "
                    "low variance signals the LLM collapsed to a default answer.",
    )
    inflation_warning: bool = False  # set when overall resonance > 8.5 across both cohorts
    warnings: list[str] = Field(default_factory=list)
    recommended_action: str = ""


# ---------------------------------------------------------------------------
# Synthesis — final user-facing summary
# ---------------------------------------------------------------------------

class QuoteSource(BaseModel):
    """A representative quote with the agent who said it (when known)."""
    quote: str
    agent_idx: Optional[int] = None
    segment: Optional[str] = None


class FrictionTheme(BaseModel):
    theme: str
    count: int
    severity: Literal["high", "medium", "low"] = "medium"
    example_quotes: list[QuoteSource] = Field(default_factory=list)
    # Which cohort the theme was clustered from. "both" = single-screen
    # mode, or A/B tie where both cohorts contributed.
    cohort: Literal["variant_a", "variant_b", "both"] = "both"
    # LLM-authored phrasings so the UI never has to invert a negative theme
    # label into an action/need with brittle regex. Empty on pre-existing runs;
    # the frontend falls back to deterministic phrasing when blank.
    recommended_action: str = ""  # imperative fix, e.g. "Add concrete use cases"
    user_need: str = ""  # positive need phrase, e.g. "clear, specific use cases"


class Synthesis(BaseModel):
    # ── Cohort-resonance verdict (v0.3) ──────────────────────────────────────
    cohort_resonance: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="{variant_a: {motivation: 6.2, ...}, variant_b: {...}}",
    )
    cohort_resonance_overall: dict[str, float] = Field(
        default_factory=dict,
        description="{variant_a: 5.8, variant_b: 7.2} — weighted mean per cohort",
    )
    resonance_gap: float = 0.0                   # cohort_b_overall - cohort_a_overall
    directional_winner: Literal["variant_a", "variant_b", "tie"] = "tie"
    gap_significance: Literal["strong", "moderate", "weak", "tie"] = "tie"
    per_persona_resonance: dict[str, dict[str, dict[str, float]]] = Field(
        default_factory=dict,
        description="{segment: {variant_a: {dim: score}, variant_b: {dim: score}}}",
    )
    # ── Narrative agents (v0.3 P2) ───────────────────────────────────────────
    structural_diff: list[str] = Field(
        default_factory=list,
        description="Factual list of design differences. NO winner judgment.",
    )
    hypothesis_pros: dict[str, list[str]] = Field(
        default_factory=dict,
        description="{variant_a: 3 reasons it may work, variant_b: 3 reasons it may work}",
    )
    hypothesis_cons: dict[str, list[str]] = Field(
        default_factory=dict,
        description="{variant_a: 3 reasons it may fail, variant_b: 3 reasons it may fail}",
    )
    narrative: str = Field(
        default="",
        description="Multi-paragraph PM-facing story from cohort_narrative agent.",
    )
    # ── Diagnostics (kept) ────────────────────────────────────────────────────
    coverage_score: int = Field(default=0, ge=0, le=100)
    top_friction: list[FrictionTheme] = Field(default_factory=list)
    what_worked_themes: list[FrictionTheme] = Field(default_factory=list)
    segment_splits: dict[str, dict[str, float]] = Field(default_factory=dict)
    recommendation: str = ""
    one_line_summary: str = ""
    confound_warning: Optional[str] = None
    trust_signal_gaps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Fidelity — Phase 7 calibration output (Arize-track)
# ---------------------------------------------------------------------------

class FidelityReport(BaseModel):
    """How faithfully agents simulated their personas in this run.

    `persona_consistency` is the LLM-as-a-Judge signal; `rationale_coherence`
    is the deterministic code-based signal. Two independent eval columns let
    Phoenix triangulate without a single LLM hallucination dominating.
    """
    persona_consistency: float = Field(ge=0.0, le=1.0)
    agents_drifted: int = 0
    rationale_coherence: float = Field(default=1.0, ge=0.0, le=1.0)
    agents_incoherent: int = 0
    eval_explanations: list[str] = Field(default_factory=list)
    drifted_agent_indices: list[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Run document — the stigmergy shared state
# ---------------------------------------------------------------------------

RunStatus = Literal[
    "pending",
    "normalizing",
    "building_scenarios",
    "simulating",
    "auditing",
    "synthesizing",
    "narrating",
    "calibrating",
    "complete",
    "failed",
]


class Run(BaseModel):
    """The full shared-state document. Each agent reads/writes its slice."""
    run_id: str
    status: RunStatus = "pending"
    phases_complete: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Inputs (set at creation)
    goal: str
    audience_raw: str = ""  # legacy free-text path
    audience_preset: Optional[AudiencePreset] = None  # v0.3 chip selector input
    persona_source: Literal["paste", "ga4", "auto", "library", "preset"] = "paste"
    variant_a_path: str
    variant_b_path: Optional[str] = None  # None = single-screen mode

    # Agent outputs (set incrementally by each agent — the pheromone trail)
    brief: Optional[Brief] = None
    scenarios: list[ScenarioCard] = Field(default_factory=list)
    agent_allocations: list[dict] = Field(default_factory=list)
    simulation_results: list[SimResult] = Field(default_factory=list)
    audit: Optional[AuditReport] = None
    synthesis: Optional[Synthesis] = None
    fidelity: Optional[FidelityReport] = None

    error: Optional[str] = None


# ---------------------------------------------------------------------------
# API shapes
# ---------------------------------------------------------------------------

class CreateRunResponse(BaseModel):
    run_id: str
    status: RunStatus
    stream_url: str
    dashboard_url: str