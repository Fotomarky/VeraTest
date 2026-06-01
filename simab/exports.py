"""Exports — translate run results into formats PMs and teams actually use.

The dashboard is for analysis. These exports are for sharing:
- Markdown: paste into Notion / Linear / Jira / PRD docs / Slack
- PM summary: simplified language that hides technical jargon
- Standalone HTML: shareable link that works without the Next.js frontend
"""
from __future__ import annotations
from typing import Optional

from .models import Run


# ---------------------------------------------------------------------------
# PM-friendly translation
# ---------------------------------------------------------------------------

# Technical → product-manager phrasing. The dashboard speaks in audit jargon;
# PRDs need plain language.
_PM_TRANSLATIONS = {
    "Cohort imbalance":          "Sample split between the two designs wasn't even — interpret with care",
    "Score collapse":            "AI gave nearly identical scores across personas — possible model collapse",
    "Resonance inflation":       "Scores skewed high overall — trust the gap between designs, not the absolute numbers",
    "Rationale coherence":       "Internal consistency check",
    "confidence collapse":       "low overall confidence — both designs may have unresolved issues",
    "scenario diversity":        "audience variety",
    "stigmergy":                 "automated coordination",
}


def pm_translate(text: str) -> str:
    for tech, pm in _PM_TRANSLATIONS.items():
        text = text.replace(tech, pm)
    return text


def pm_summary(run: Run) -> dict:
    """Plain-language summary fit for a PRD or a Slack message.

    Returns the same data as the synthesis, but with technical warnings
    rephrased and trust levels translated to a recommendation tone.
    """
    if not run.synthesis or not run.audit:
        return {
            "status": run.status,
            "ready": False,
            "message": "Run is still in progress. Check back in a minute.",
        }

    synth = run.synthesis
    audit = run.audit

    trust_phrasing = {
        "high":   "Findings are reliable enough to act on.",
        "medium": "Findings are directional — useful for narrowing options, but validate with real traffic before big bets.",
        "low":    "Findings are unreliable. Address the warnings before acting.",
    }

    sig_phrasing = {
        "strong":   "clearly stronger",
        "moderate": "moderately stronger",
        "weak":     "slightly stronger",
        "tie":      "similarly",
    }
    sig = synth.gap_significance
    if synth.directional_winner == "variant_a":
        headline = f"Variant A resonates {sig_phrasing[sig]}"
    elif synth.directional_winner == "variant_b":
        headline = f"Variant B resonates {sig_phrasing[sig]}"
    else:
        headline = "No clear winner — designs resonate similarly"

    a_overall = synth.cohort_resonance_overall.get("variant_a", 0.0)
    b_overall = synth.cohort_resonance_overall.get("variant_b", 0.0)

    return {
        "ready": True,
        "headline": headline,
        "confidence": audit.trust_level,
        "confidence_note": trust_phrasing[audit.trust_level],
        "summary": synth.one_line_summary,
        "recommendation": synth.recommendation,
        "top_friction": [
            {"issue": t.theme, "severity": t.severity, "mentioned_by": t.count}
            for t in synth.top_friction[:3]
        ],
        "caveats": [pm_translate(w) for w in audit.warnings],
        "resonance_scores": {
            "variant_a": f"{a_overall:.1f}/10",
            "variant_b": f"{b_overall:.1f}/10",
            "gap":       f"{synth.resonance_gap:+.1f}",
            "significance": sig,
        },
    }


# ---------------------------------------------------------------------------
# Markdown export — paste this into Notion, Linear, Slack, anywhere
# ---------------------------------------------------------------------------

def to_markdown(run: Run, share_url: Optional[str] = None) -> str:
    """Generate a markdown report suitable for pasting into PRDs or tickets."""
    if not run.synthesis or not run.audit:
        return f"# Pretest in progress\n\n**Run:** `{run.run_id}` · status: _{run.status}_"

    synth = run.synthesis
    audit = run.audit
    pm = pm_summary(run)

    lines = [
        f"# UX Pretest — {run.goal}",
        "",
        f"**Decision:** {pm['headline']}  ",
        f"**Confidence:** {pm['confidence'].upper()} — {pm['confidence_note']}",
        "",
        f"> {synth.one_line_summary}",
        "",
    ]

    # Caveats up front if confidence isn't high
    if audit.trust_level != "high" and audit.warnings:
        lines.append("## ⚠ Caveats")
        for w in audit.warnings:
            lines.append(f"- {pm_translate(w)}")
        lines.append("")

    # Cohort resonance result
    lines.append("## Result")
    lines.append("")
    lines.append("| Variant | Resonance |")
    lines.append("|---|---|")
    for variant in ("variant_a", "variant_b"):
        score = synth.cohort_resonance_overall.get(variant, 0)
        label = variant.replace("_", " ").title()
        marker = " ← directional winner" if variant == synth.directional_winner else ""
        lines.append(f"| {label}{marker} | {score:.1f}/10 |")
    sign = "+" if synth.resonance_gap >= 0 else ""
    lines.append(
        f"\n**Gap:** {sign}{synth.resonance_gap:.1f} "
        f"(significance: _{synth.gap_significance}_)\n"
    )
    lines.append(
        "_Resonance measures how well each design fits the audience's motives, "
        "beliefs and situation. It is a necessary condition for conversion, "
        "not a prediction of conversion rate._"
    )
    lines.append("")

    # Narrative (v0.3 P2: cohort_narrative agent output)
    if synth.narrative:
        lines.append("## Analysis")
        lines.append("")
        lines.append(synth.narrative)
        lines.append("")

    # Structural diff (v0.3 P2: factual differences only, no winner judgment)
    if synth.structural_diff:
        lines.append("## What's different between the variants")
        lines.append("")
        for d in synth.structural_diff[:10]:
            lines.append(f"- {d}")
        lines.append("")

    # Symmetric hypothesis
    if synth.hypothesis_pros or synth.hypothesis_cons:
        lines.append("## Tradeoffs (balanced view)")
        lines.append("")
        for variant in ("variant_a", "variant_b"):
            label = variant.replace("_", " ").title()
            pros = synth.hypothesis_pros.get(variant, [])
            cons = synth.hypothesis_cons.get(variant, [])
            if not (pros or cons):
                continue
            lines.append(f"**{label}**")
            for p in pros:
                lines.append(f"- ✓ {p}")
            for c in cons:
                lines.append(f"- ✗ {c}")
            lines.append("")

    # Friction
    if synth.top_friction:
        lines.append("## Top friction (in the losing variant)")
        lines.append("")
        for t in synth.top_friction[:5]:
            sev_marker = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.severity, "·")
            lines.append(f"- {sev_marker} **{t.theme}** ({t.count} mentions)")
            if t.example_quotes:
                lines.append(f"  > _\"{t.example_quotes[0]}\"_")
        lines.append("")

    # Segment splits (per-segment resonance overall, per cohort)
    if synth.segment_splits:
        lines.append("## Per-segment resonance")
        lines.append("")
        for seg, splits in list(synth.segment_splits.items())[:6]:
            parts = ", ".join(
                f"{k.replace('_', ' ')}: {v:.1f}/10"
                for k, v in splits.items() if v > 0
            )
            lines.append(f"- **{seg}** — {parts}")
        lines.append("")

    # Recommendation
    if synth.recommendation:
        lines.append("## Recommendation")
        lines.append("")
        lines.append(synth.recommendation)
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"_Run `{run.run_id}` · coverage {synth.coverage_score}/100_")
    if share_url:
        lines.append(f"_Full dashboard: {share_url}_")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Standalone HTML share page — no Next.js required
# ---------------------------------------------------------------------------

def to_share_html(run: Run) -> str:
    """A single self-contained HTML page that anyone can open.

    No frontend build required. Hosted at /share/{run_id}. PMs can send
    this URL anywhere — Slack, email, a PRD — and it just works.
    """
    pm = pm_summary(run)
    md_content = to_markdown(run)

    if not pm["ready"]:
        body = f"<p>Run is still in progress (status: <em>{run.status}</em>).</p>"
    else:
        # Render simple HTML — keep it inline so no build step is needed
        rows = []
        for friction in pm["top_friction"]:
            sev_color = {
                "high": "#ef4444", "medium": "#f59e0b", "low": "#10b981"
            }.get(friction["severity"], "#6b7280")
            rows.append(
                f'<li><span style="color:{sev_color};font-weight:bold;">●</span> '
                f'{friction["issue"]} <span style="color:#6b7280;font-size:0.85em;">'
                f'({friction["mentioned_by"]} mentions)</span></li>'
            )
        friction_html = "<ul>" + "".join(rows) + "</ul>" if rows else "<p>—</p>"

        caveat_html = ""
        if pm["caveats"]:
            caveat_html = (
                '<div style="background:#fef3c7;border-left:3px solid #f59e0b;'
                'padding:12px;margin:16px 0;border-radius:4px;">'
                '<strong>Caveats</strong><ul style="margin:8px 0 0 0;">'
                + "".join(f"<li>{c}</li>" for c in pm["caveats"])
                + "</ul></div>"
            )

        body = f"""
        <div style="background:#dbeafe;padding:16px;border-radius:8px;margin-bottom:16px;">
          <div style="font-size:0.85em;color:#1e40af;font-weight:600;text-transform:uppercase;">
            Decision
          </div>
          <div style="font-size:1.5em;margin-top:4px;">{pm['headline']}</div>
          <div style="color:#475569;margin-top:8px;">{pm['summary']}</div>
        </div>
        {caveat_html}
        <h3>Top friction</h3>
        {friction_html}
        <h3>Recommendation</h3>
        <p>{run.synthesis.recommendation if run.synthesis else '—'}</p>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{run.goal} — SimAB Pretest</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 720px; margin: 40px auto; padding: 0 20px; color: #1f2937;
         line-height: 1.6; }}
  h1 {{ font-size: 1.5em; margin: 0 0 4px 0; }}
  h3 {{ font-size: 1.05em; margin: 24px 0 8px 0; }}
  ul {{ padding-left: 20px; }}
  .meta {{ color: #6b7280; font-size: 0.85em; margin-bottom: 24px; }}
  .actions {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #e5e7eb; }}
  .actions a {{ color: #2563eb; text-decoration: none; margin-right: 16px; font-size: 0.9em; }}
  pre {{ background: #f3f4f6; padding: 12px; border-radius: 4px; overflow-x: auto;
         font-size: 0.8em; }}
</style>
</head>
<body>
  <h1>{run.goal}</h1>
  <div class="meta">Pretest run · <code>{run.run_id}</code></div>
  {body}
  <div class="actions">
    <a href="/api/runs/{run.run_id}/export.md">Copy as markdown</a>
    <a href="/api/runs/{run.run_id}">View JSON</a>
  </div>
  <details style="margin-top:24px;">
    <summary style="cursor:pointer;color:#6b7280;font-size:0.9em;">
      Markdown source (paste into PRD / Notion / Linear)
    </summary>
    <pre>{md_content.replace("<", "&lt;").replace(">", "&gt;")}</pre>
  </details>
</body>
</html>
"""
