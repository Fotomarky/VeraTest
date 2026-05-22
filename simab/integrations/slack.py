"""Slack integration — post pretest results to a team channel.

Uses Slack incoming webhooks (no app install required). Set
SIMAB_SLACK_WEBHOOK_URL in env to enable auto-posting on run completion.

To create a webhook:
1. https://api.slack.com/messaging/webhooks
2. Create a Slack app, enable incoming webhooks
3. Add the webhook URL to your env

This is what makes SimAB show up where PMs already work: when a run
completes, the team sees the verdict in Slack and can click through to
the share page — no one has to remember to check a dashboard.
"""
from __future__ import annotations
import logging
import os
from typing import Optional

import httpx

from ..exports import pm_summary
from ..models import Run

log = logging.getLogger(__name__)


def _get_webhook_url() -> Optional[str]:
    return os.environ.get("SIMAB_SLACK_WEBHOOK_URL") or None


def _build_slack_message(run: Run, share_url: str) -> dict:
    """Slack Block Kit message — clean, scannable, with action link."""
    pm = pm_summary(run)

    if not pm["ready"]:
        return {
            "text": f"SimAB run `{run.run_id}` is still in progress."
        }

    # Color based on confidence
    color = {
        "high": "#10b981",   # green
        "medium": "#f59e0b",  # amber
        "low": "#ef4444",     # red
    }.get(pm["confidence"], "#6b7280")

    fields = []
    for friction in pm["top_friction"][:3]:
        sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(friction["severity"], "·")
        fields.append({
            "type": "mrkdwn",
            "text": f"{sev} *{friction['issue']}* — {friction['mentioned_by']} mentions",
        })

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": pm["headline"]},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_{pm['summary']}_"},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn",
                 "text": f"Goal: *{run.goal}*  ·  Confidence: *{pm['confidence'].upper()}*"},
            ],
        },
    ]

    if pm["caveats"]:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "⚠ *Caveats*\n" + "\n".join(f"• {c}" for c in pm["caveats"]),
            },
        })

    if fields:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Top friction in losing variant:*"},
            "fields": fields,
        })

    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View full report"},
                "url": share_url,
                "style": "primary",
            },
        ],
    })

    return {
        "text": f"SimAB result: {pm['headline']}",  # fallback for notifications
        "attachments": [{"color": color, "blocks": blocks}],
    }


async def post_run_to_slack(run: Run, share_url: str) -> bool:
    """Post a completed run's result to the configured Slack webhook.

    Returns True if posted, False if no webhook configured or post failed.
    Safe to call on every run completion — it no-ops without config.
    """
    webhook = _get_webhook_url()
    if not webhook:
        return False

    payload = _build_slack_message(run, share_url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook, json=payload)
            if resp.status_code >= 400:
                log.warning(f"Slack post failed: {resp.status_code} {resp.text[:200]}")
                return False
        log.info(f"[{run.run_id}] posted result to Slack")
        return True
    except Exception as e:
        log.warning(f"Slack post error (non-fatal): {e}")
        return False
