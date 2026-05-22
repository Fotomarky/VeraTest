"""GA4 connector — optional.

Pulls last N months of audience data from a user's Google Analytics 4 property
and converts it into traffic-weighted scenario cards via one LLM call.

Setup (free):
1. Create OAuth credentials at https://console.cloud.google.com/apis/credentials
2. Enable Google Analytics Data API on the same project
3. Set GA4_CLIENT_ID, GA4_CLIENT_SECRET, GA4_REDIRECT_URI in env

This entire integration is ~150 lines. If GA4 env vars are missing, the
import still works; only the actual API calls will fail with a clear message.
"""
from __future__ import annotations
import json
import logging
from typing import Any

from ..config import CONFIG
from ..llm import MODEL_PRO, generate
from ..models import ScenarioCard

log = logging.getLogger(__name__)


GA4_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def _require_credentials() -> None:
    if not CONFIG.ga4_client_id or not CONFIG.ga4_client_secret:
        raise RuntimeError(
            "GA4 connector not configured. Set GA4_CLIENT_ID and "
            "GA4_CLIENT_SECRET in your environment."
        )


def authorization_url() -> str:
    """Return the consent URL the user should visit to grant access."""
    _require_credentials()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CONFIG.ga4_client_id,
                "client_secret": CONFIG.ga4_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [CONFIG.ga4_redirect_uri],
            }
        },
        scopes=GA4_SCOPES,
    )
    flow.redirect_uri = CONFIG.ga4_redirect_uri
    url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return url


def exchange_code_for_token(code: str) -> dict:
    """Trade the OAuth callback code for an access/refresh token pair."""
    _require_credentials()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CONFIG.ga4_client_id,
                "client_secret": CONFIG.ga4_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [CONFIG.ga4_redirect_uri],
            }
        },
        scopes=GA4_SCOPES,
    )
    flow.redirect_uri = CONFIG.ga4_redirect_uri
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def _fetch_ga4_report(property_id: str, access_token: str, months: int) -> list[dict]:
    """Pull top audience dimensions from GA4."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    from google.oauth2.credentials import Credentials

    creds = Credentials(token=access_token)
    client = BetaAnalyticsDataClient(credentials=creds)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=f"{months}monthsAgo", end_date="today")],
        dimensions=[
            Dimension(name="deviceCategory"),
            Dimension(name="sessionDefaultChannelGroup"),
            Dimension(name="newVsReturning"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="conversions"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=30,
    )

    response = client.run_report(request)
    rows = []
    for row in response.rows:
        d = {h.name: v.value for h, v in zip(response.dimension_headers, row.dimension_values)}
        m = {h.name: float(v.value) for h, v in zip(response.metric_headers, row.metric_values)}
        rows.append({**d, **m})
    return rows


SYNTHESIS_PROMPT = """\
Below is 6 months of Google Analytics traffic data for a landing page with
this conversion goal: {goal}

Collapse this raw segment data into exactly 5 personas that represent the
real audience, weighted by their share of traffic. The traffic_weight
across all 5 personas must sum to ~1.0.

Each persona must match the ScenarioCard schema with these fields:
id, segment, intent, decision_style, device, traffic_source, context,
constraints, time_pressure, price_sensitivity, traffic_weight, locale.

GA4 DATA:
{rows_json}

Respond with ONLY: {{"personas": [...]}} as a JSON array of 5 personas.
"""


async def build_personas_from_ga4(
    property_id: str, access_token: str, goal: str, months: int = 6
) -> list[ScenarioCard]:
    """End-to-end: GA4 API call + LLM clustering. Returns 5 weighted personas."""
    rows = _fetch_ga4_report(property_id, access_token, months)
    if not rows:
        log.warning("GA4 returned no rows; falling back to inferred personas")
        return []

    raw = await generate(
        model=MODEL_PRO,
        prompt=SYNTHESIS_PROMPT.format(
            goal=goal, rows_json=json.dumps(rows[:20], indent=2)
        ),
        response_schema={},
        temperature=0.2,
    )
    personas_data = raw.get("personas", []) if isinstance(raw, dict) else raw
    personas: list[ScenarioCard] = []
    for i, p in enumerate(personas_data[:5]):
        try:
            p["id"] = f"sc_ga4_{i+1:03d}"
            personas.append(ScenarioCard.model_validate(p))
        except Exception as e:
            log.warning(f"Persona {i} parse failed: {e}")
    return personas
