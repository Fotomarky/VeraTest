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
# Brief — output of the BriefNormalizer agent
# ---------------------------------------------------------------------------

class Brief(BaseModel):
    conversion_goal: str
    variant_a_summary: str
    variant_b_summary: str
    key_differences: list[str]
    test_type: Literal["pre_release", "post_release"] = "pre_release"
    inferred_personas: list[ScenarioCard] = Field(default_factory=list)
    needs_clarification: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Simulation result — one sim agent's output
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Audit — output of the BiasAuditor agent
# ---------------------------------------------------------------------------

class AuditReport(BaseModel):
    trust_level: Literal["high", "medium", "low"]
    order_bias_detected: bool
    first_position_win_rate: float  # 0-1; expected ~0.5 if no bias
    confidence_collapse: bool
    low_confidence_rate: float
    avg_rationale_coherence: float  # 0-1
    segment_divergence: dict[str, dict[str, int]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    recommended_action: str


# ---------------------------------------------------------------------------
# Synthesis — final user-facing summary
# ---------------------------------------------------------------------------

class FrictionTheme(BaseModel):
    theme: str
    count: int
    severity: Literal["high", "medium", "low"] = "medium"
    example_quotes: list[str] = Field(default_factory=list)


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
    audience_raw: str = ""  # paste mode input
    persona_source: Literal["paste", "ga4", "auto", "library"] = "paste"
    variant_a_path: str
    variant_b_path: str

    # Agent outputs (set incrementally by each agent — the pheromone trail)
    brief: Optional[Brief] = None
    scenarios: list[ScenarioCard] = Field(default_factory=list)
    agent_allocations: list[dict] = Field(default_factory=list)
    simulation_results: list[SimResult] = Field(default_factory=list)
    audit: Optional[AuditReport] = None
    synthesis: Optional[Synthesis] = None

    error: Optional[str] = None


# ---------------------------------------------------------------------------
# API shapes
# ---------------------------------------------------------------------------

class CreateRunResponse(BaseModel):
    run_id: str
    status: RunStatus
    stream_url: str
    dashboard_url: str