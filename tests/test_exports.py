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

    # Audit with low trust to exercise the warning paths
    audit = AuditReport(
        trust_level="medium",
        order_bias_detected=False,
        first_position_win_rate=0.55,
        confidence_collapse=False,
        low_confidence_rate=0.2,
        avg_rationale_coherence=0.78,
        warnings=["Position bias detected: 70% favored the first-shown image"],
        recommended_action="Results are directional. Validate before bigger bets.",
    )
    await state.write_audit(run_id, audit)

    synthesis = Synthesis(
        winner="variant_b",
        raw_vote={"variant_a": 6, "variant_b": 14},
        weighted_vote={"variant_a": 0.32, "variant_b": 0.68},
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
            "SaaS evaluator": {"variant_a": 0.25, "variant_b": 0.75},
            "Mobile browser": {"variant_a": 0.45, "variant_b": 0.55},
        },
        recommendation="Ship Variant B but fix the pricing tier ambiguity before scaling traffic.",
        one_line_summary="Variant B wins clearly with desktop evaluators; "
                         "mobile audience is more split.",
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
    # Technical phrase should be translated
    assert "skewed by which design users saw first" in pm["caveats"][0]
    assert "Position bias detected" not in pm["caveats"][0]


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

    # Must contain the headline decision
    assert "Variant B is the better choice" in md
    # Must contain the friction theme
    assert "Pricing tier is unclear" in md
    # Must contain segment splits
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
