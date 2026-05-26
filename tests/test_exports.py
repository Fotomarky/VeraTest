"""Tests for the PM-facing surfaces: markdown export, summary translation,
share page, Slack message construction."""
import pytest

from simab import exports, state
from simab.integrations.slack import _build_slack_message
from simab.models import (
    AuditReport, Brief, FrictionTheme, ScenarioCard, SimResult, Synthesis,
)


async def _build_complete_run(run_id_out: list[str]) -> str:
    """Helper: create a run and populate it with realistic synthetic data."""
    run_id = await state.create_run(
        goal="sign up for free trial",
        audience_raw="SaaS evaluators on desktop",
        persona_source="paste",
        variant_a_path="/tmp/a.png",
        variant_b_path="/tmp/b.png",
    )
    run_id_out.append(run_id)

    brief = Brief(
        conversion_goal="sign up for free trial",
        variant_a_summary="Minimal headline, single CTA",
        variant_b_summary="Long-form copy, pricing table visible",
        key_differences=["headline length", "pricing visibility", "CTA color"],
        inferred_personas=[
            ScenarioCard(id="sc_001", segment="SaaS evaluator", traffic_weight=0.6),
            ScenarioCard(id="sc_002", segment="Mobile browser", traffic_weight=0.4),
        ],
    )
    await state.write_brief(run_id, brief)

    # Audit with medium trust + a translatable warning to exercise the PM path
    audit = AuditReport(
        trust_level="medium",
        confidence_collapse=False,
        low_confidence_rate=0.2,
        avg_rationale_coherence=0.78,
        cohort_balance={"variant_a": 10, "variant_b": 10},
        cohort_persona_balance={
            "SaaS evaluator": {"variant_a": 6, "variant_b": 6},
            "Mobile browser": {"variant_a": 4, "variant_b": 4},
        },
        per_dim_variance={
            "motivation": 1.4, "identity": 1.1, "situation": 1.5,
            "beliefs": 1.2, "ability": 1.6, "trigger": 1.3,
        },
        inflation_warning=True,
        warnings=["Resonance inflation: both cohorts averaged above 8.5/10."],
        recommended_action="Results are directional. Validate before scaling traffic.",
    )
    await state.write_audit(run_id, audit)

    synthesis = Synthesis(
        cohort_resonance={
            "variant_a": {"motivation": 5, "identity": 5, "situation": 4,
                          "beliefs": 5, "ability": 6, "trigger": 5},
            "variant_b": {"motivation": 7, "identity": 7, "situation": 7,
                          "beliefs": 7, "ability": 8, "trigger": 7},
        },
        cohort_resonance_overall={"variant_a": 5.0, "variant_b": 7.15},
        resonance_gap=2.15,
        directional_winner="variant_b",
        gap_significance="strong",
        per_persona_resonance={
            "SaaS evaluator": {
                "variant_a": {"motivation": 5, "identity": 5, "situation": 4,
                              "beliefs": 5, "ability": 6, "trigger": 5},
                "variant_b": {"motivation": 8, "identity": 7, "situation": 7,
                              "beliefs": 7, "ability": 8, "trigger": 8},
            },
        },
        coverage_score=82,
        top_friction=[
            FrictionTheme(
                theme="Pricing tier is unclear",
                count=11,
                severity="high",
                example_quotes=["I couldn't tell which tier was the free one"],
            ),
            FrictionTheme(
                theme="CTA buried below the fold",
                count=7,
                severity="medium",
                example_quotes=["Had to scroll to find the signup button"],
            ),
        ],
        segment_splits={
            "SaaS evaluator": {"variant_a": 5.2, "variant_b": 7.4},
            "Mobile browser": {"variant_a": 4.6, "variant_b": 6.9},
        },
        recommendation="Ship Variant B but fix the pricing tier ambiguity before scaling traffic.",
        one_line_summary="Variant B resonates clearly more strongly with desktop "
                         "evaluators; mobile audience shows a smaller gap.",
        trust_signal_gaps=["Testimonials", "Money-back guarantee"],
    )
    await state.write_synthesis(run_id, synthesis)

    return run_id


@pytest.mark.asyncio
async def test_pm_summary_translates_warnings():
    run_id_holder: list[str] = []
    run_id = await _build_complete_run(run_id_holder)
    run = await state.get_run(run_id)

    pm = exports.pm_summary(run)
    assert pm["ready"] is True
    assert pm["confidence"] == "medium"
    assert "Variant B" in pm["headline"]
    # Technical phrase should be translated to PM-friendly language
    assert any("trust the gap between designs" in c for c in pm["caveats"])
    assert all("Resonance inflation" not in c for c in pm["caveats"])
    # New v0.3 resonance_scores block must be present
    assert pm["resonance_scores"]["variant_a"] == "5.0/10"
    assert pm["resonance_scores"]["variant_b"] == "7.2/10"
    assert pm["resonance_scores"]["gap"] == "+2.1"  # 2.15 rounds down via banker's rounding
    assert pm["resonance_scores"]["significance"] == "strong"


@pytest.mark.asyncio
async def test_pm_summary_handles_incomplete_run():
    run_id = await state.create_run(
        goal="g", audience_raw="", persona_source="paste",
        variant_a_path="/a", variant_b_path="/b",
    )
    run = await state.get_run(run_id)
    pm = exports.pm_summary(run)
    assert pm["ready"] is False
    assert "in progress" in pm["message"].lower()


@pytest.mark.asyncio
async def test_markdown_export_contains_key_sections():
    run_id_holder: list[str] = []
    run_id = await _build_complete_run(run_id_holder)
    run = await state.get_run(run_id)

    md = exports.to_markdown(run, share_url="https://example.com/share/x")

    # Must contain the new headline phrasing
    assert "Variant B resonates" in md
    # Must contain the resonance score table
    assert "7.2/10" in md
    assert "directional winner" in md
    # Must contain the friction theme
    assert "Pricing tier is unclear" in md
    # Must contain per-segment resonance
    assert "SaaS evaluator" in md
    # Must contain the recommendation
    assert "fix the pricing tier" in md
    # Must contain the share URL footer
    assert "https://example.com/share/x" in md
    # Must contain caveats since trust is medium
    assert "Caveats" in md


@pytest.mark.asyncio
async def test_markdown_export_for_incomplete_run():
    run_id = await state.create_run(
        goal="g", audience_raw="", persona_source="paste",
        variant_a_path="/a", variant_b_path="/b",
    )
    run = await state.get_run(run_id)
    md = exports.to_markdown(run)
    assert "in progress" in md.lower()
    assert run.run_id in md


@pytest.mark.asyncio
async def test_share_html_self_contained():
    run_id_holder: list[str] = []
    run_id = await _build_complete_run(run_id_holder)
    run = await state.get_run(run_id)

    html = exports.to_share_html(run)
    # No external JS/CSS — fully inline
    assert "<script" not in html.lower() or "src=" not in html
    assert "<style>" in html
    # Has the export links so PMs can copy the markdown
    assert "/api/runs/" in html
    assert "export.md" in html
    # Contains the actual decision
    assert "Variant B" in html


@pytest.mark.asyncio
async def test_slack_message_structure():
    run_id_holder: list[str] = []
    run_id = await _build_complete_run(run_id_holder)
    run = await state.get_run(run_id)

    msg = _build_slack_message(run, share_url="https://example.com/share/x")

    # Slack expects "text" as a fallback and "attachments" for rich content
    assert "text" in msg
    assert "Variant B" in msg["text"]
    attachments = msg.get("attachments", [])
    assert len(attachments) > 0
    blocks = attachments[0]["blocks"]
    # Header, section, context at minimum
    assert any(b["type"] == "header" for b in blocks)
    assert any(b["type"] == "actions" for b in blocks)
    # Action button must link to the share URL
    actions = next(b for b in blocks if b["type"] == "actions")
    assert actions["elements"][0]["url"] == "https://example.com/share/x"
