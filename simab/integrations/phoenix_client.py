"""Phoenix Python client helpers — cross-run memory substrate.

VeraTest has two memory substrates:
  * SQLite — within-run pheromone trail (one run, six agents coordinating).
  * Phoenix — cross-run learning memory (datasets of drifted agents,
    SpanEvaluations on every agent invocation, Experiments for prompt A/B).

These three helpers are the API surface the FidelityAuditor (Task 9) and
the Panel Recruiter / ScenarioBuilder (Task 8) use to write to and read
from the cross-run substrate.

ALL helpers degrade to silent no-ops when:
  - The Phoenix dependency (`arize-phoenix-client`) isn't installed, OR
  - Neither PHOENIX_COLLECTOR_ENDPOINT nor PHOENIX_API_KEY is set.

That way unit tests, free-tier deploys, and the dev loop all work without
the Phoenix extra. The full integration is exercised in Task 16's e2e.
"""
from __future__ import annotations
import hashlib
import logging
import re
from typing import Any

from ..config import CONFIG

log = logging.getLogger(__name__)

_client: Any | None = None
_disabled_warned = False


def _reset_client_for_test() -> None:
    """Drop the cached client. Test hook — used in tests/test_calibration.py
    to ensure each test gets a fresh, env-aware client state."""
    global _client, _disabled_warned
    _client = None
    _disabled_warned = False


def _get_client():
    """Lazily build a phoenix.client.Client. Returns None when unavailable."""
    global _client, _disabled_warned
    if _client is not None:
        return _client
    if not (CONFIG.phoenix_endpoint or CONFIG.phoenix_api_key):
        if not _disabled_warned:
            log.info("Phoenix client disabled — no endpoint or api key set")
            _disabled_warned = True
        return None
    try:
        from phoenix.client import Client
    except ImportError:
        if not _disabled_warned:
            log.warning(
                "Phoenix client not installed — `pip install 'simab[phoenix]'`"
            )
            _disabled_warned = True
        return None
    _client = Client(
        base_url=CONFIG.phoenix_endpoint,
        api_key=CONFIG.phoenix_api_key,
    )
    return _client


def audience_signature(audience: str) -> str:
    """Stable hash key for grouping runs by audience similarity.

    We don't want every micro-edit ('CI tools' vs 'CI/CD tooling') to land
    in a different history bucket — a 16-hex SHA1 of the normalized
    audience string is plenty discriminating without being noisy. The
    normalization strips punctuation, lowercases, and collapses whitespace.
    """
    normalized = re.sub(r"[^a-z0-9 ]+", "", audience.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def get_persona_drift_history(audience_signature: str) -> dict[str, float]:
    """Return {persona_archetype: historical_drift_rate} for prior runs of
    the same audience signature. Empty dict when Phoenix is unavailable.

    Schema convention: Phoenix Dataset 'drifted_agents' carries
    metadata.audience_signature and inputs.persona_archetype on each row.
    Each row represents ONE drift event. Drift rate = drift events for
    that archetype / total runs touching that archetype (proxied as
    distinct run_ids in metadata).
    """
    client = _get_client()
    if client is None:
        return {}
    try:
        dataset = client.datasets.get_dataset(name="drifted_agents")
    except Exception as e:
        log.debug(f"drifted_agents dataset not yet present: {e}")
        return {}

    drift_counts: dict[str, int] = {}
    runs_seen: dict[str, set[str]] = {}  # archetype -> set of run_ids seen
    for example in (getattr(dataset, "examples", None) or []):
        meta = getattr(example, "metadata", None) or {}
        if meta.get("audience_signature") != audience_signature:
            continue
        arche = (getattr(example, "input", None) or {}).get(
            "persona_archetype", "unknown"
        )
        rid = meta.get("run_id", "")
        drift_counts[arche] = drift_counts.get(arche, 0) + 1
        runs_seen.setdefault(arche, set()).add(rid)
    if not drift_counts:
        return {}
    return {
        a: drift_counts[a] / max(len(runs_seen[a]), 1) for a in drift_counts
    }


def append_drifted_agents(
    *,
    run_id: str,
    audience_signature: str,
    rows: list[dict[str, Any]],
) -> None:
    """Append drifted-agent rows to the persistent 'drifted_agents' Phoenix
    Dataset so they can train the Panel Recruiter on the next run and feed
    the calibration Experiment for the demo."""
    if not rows:
        return
    client = _get_client()
    if client is None:
        return
    try:
        client.datasets.append_to_dataset(
            name="drifted_agents",
            inputs=rows,
            metadata=[
                {"run_id": run_id, "audience_signature": audience_signature}
                for _ in rows
            ],
        )
    except Exception as e:
        log.warning(
            f"Failed to append drifted agents to dataset (non-fatal): {e}"
        )


def log_span_evaluations(eval_name: str, df) -> None:
    """Attach Span Evaluations (a pandas DataFrame indexed by span_id) to
    existing traces. The DataFrame should contain at minimum a `score` or
    `label` column plus the span_id index per Phoenix's eval schema."""
    client = _get_client()
    if client is None:
        return
    try:
        from phoenix.trace import SpanEvaluations
        client.log_evaluations(
            SpanEvaluations(eval_name=eval_name, dataframe=df)
        )
    except Exception as e:
        log.warning(f"Failed to log span evaluations '{eval_name}': {e}")
