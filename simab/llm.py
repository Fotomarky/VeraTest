"""Gemini API wrapper with rate limiting for the free tier.

Free tier limits (as of 2026):
- Flash-Lite: 30 RPM, 1,500 RPD, 1M TPM  (use this for 20 sim agents)
- Flash:      15 RPM,   500 RPD, 250k TPM (use for normalizer/scenario builder)
- Pro:         5 RPM,    50 RPD, 250k TPM (use sparingly — auditor, synthesizer)

The rate limiter is a simple token bucket per model. The 20 parallel sim
agents will be naturally throttled to 30 calls/min by SIMAB_SIM_CONCURRENCY=6
plus the bucket — 6 concurrent agents at ~2s per call = ~30 RPM.
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import random

from tenacity import (
    RetryCallState,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from google import genai
from google.genai import types

from .config import CONFIG

try:
    from opentelemetry import trace as _otel_trace
except ImportError:  # pragma: no cover - otel is a phoenix extra
    _otel_trace = None

log = logging.getLogger(__name__)


# Model identifiers — pick the cheapest model that does the job
MODEL_FLASH_LITE = "gemini-2.5-flash-lite"  # workhorse for sim agents
MODEL_FLASH = "gemini-2.5-flash"            # normalizer, scenario builder
MODEL_PRO = "gemini-2.5-pro"                # auditor, synthesizer (used twice/run)


@dataclass
class RateLimit:
    rpm: int  # requests per minute
    rpd: int  # requests per day


# Conservative limits — leave headroom for retries.
# SIMAB_RATE_MULTIPLIER scales every rpm/rpd (default 1.0). Bump it for offline
# benchmarks (e.g. the validation harness) where you'd rather push toward the
# real Google quota than the conservative cap. The server-side free-tier quota
# is still the hard ceiling — this only relaxes the client-side throttle.
_RATE_MULT = max(0.1, float(os.environ.get("SIMAB_RATE_MULTIPLIER", "1.0")))

# Per-call request timeout (seconds). A stalled Gemini response otherwise blocks
# the calling task forever; with a timeout it raises and tenacity retries.
_REQUEST_TIMEOUT_S = float(os.environ.get("SIMAB_REQUEST_TIMEOUT_S", "90"))


def _scaled(rpm: int, rpd: int) -> RateLimit:
    return RateLimit(rpm=max(1, round(rpm * _RATE_MULT)), rpd=max(1, round(rpd * _RATE_MULT)))


_LIMITS = {
    MODEL_FLASH_LITE: _scaled(25, 1400),  # cap below quota
    MODEL_FLASH: _scaled(12, 480),
    MODEL_PRO: _scaled(4, 45),
}


class _TokenBucket:
    """Tiny token bucket. Records timestamps; sleeps if we'd exceed the cap."""

    def __init__(self, rate: int, period: float):
        self.rate = rate
        self.period = period
        self._history: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            # Evict expired entries
            while self._history and self._history[0] <= now - self.period:
                self._history.popleft()
            if len(self._history) >= self.rate:
                # Wait until oldest entry expires
                sleep_for = self._history[0] + self.period - now + 0.05
                if sleep_for > 0:
                    log.debug(f"Rate limit: sleeping {sleep_for:.2f}s")
                    await asyncio.sleep(sleep_for)
            self._history.append(time.monotonic())


_buckets_minute: dict[str, _TokenBucket] = {}
_buckets_day: dict[str, _TokenBucket] = {}


def _get_buckets(model: str) -> tuple[_TokenBucket, _TokenBucket]:
    if model not in _buckets_minute:
        limit = _LIMITS.get(model, RateLimit(rpm=10, rpd=100))
        _buckets_minute[model] = _TokenBucket(limit.rpm, period=60.0)
        _buckets_day[model] = _TokenBucket(limit.rpd, period=86400.0)
    return _buckets_minute[model], _buckets_day[model]


# Lazy client
_client: genai.Client | None = None


class ConfigError(RuntimeError):
    """Non-retryable setup error (e.g. missing API key).

    Retrying a missing key 6 times with exponential waits turns an instant
    failure into ~2 minutes per call — across a 40-call validation run that
    burned a full hour before surfacing the real problem (2026-06-10)."""


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not CONFIG.gemini_api_key:
            raise ConfigError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/app/apikey"
            )
        # Pin to the AI Studio Developer API (api-key auth). Without vertexai=False,
        # a process-wide GOOGLE_GENAI_USE_VERTEXAI=TRUE (set for the ADK agent
        # layer) would route this api-key client to Vertex, which rejects API
        # keys with a 401. The pipeline's free-tier key is for AI Studio only.
        _client = genai.Client(api_key=CONFIG.gemini_api_key, vertexai=False)
    return _client


def _strip_json_fences(text: str) -> str:
    """Gemini sometimes wraps JSON in ```json ... ``` fences."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def _is_capacity_error(e: BaseException) -> bool:
    """True for Gemini capacity/quota errors (503 overloaded, 429 exhausted)."""
    s = str(e)
    return any(tok in s for tok in (
        "503", "UNAVAILABLE", "overloaded", "high demand",
        "429", "RESOURCE_EXHAUSTED",
    ))


_wait_transient = wait_exponential(multiplier=2, min=5, max=60)


def _wait_capacity_aware(retry_state: RetryCallState) -> float:
    """Longer, jittered backoff for capacity errors.

    503 "high demand" means the model is saturated — retrying on the standard
    5-60s curve just re-joins the stampede and burns attempts (this is what
    degraded 12/20 validation runs to abstention on 2026-06-10). Capacity
    errors wait 15s-90s with full jitter to decorrelate the 20 parallel sims;
    everything else keeps the original curve.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if exc is not None and _is_capacity_error(exc):
        cap = min(90.0, 15.0 * (2 ** (retry_state.attempt_number - 1)))
        return random.uniform(cap * 0.5, cap)
    return _wait_transient(retry_state)


def _record_retry(retry_state: RetryCallState) -> None:
    """Make retries visible in Phoenix: each failed attempt already produces
    its own error LLM span (the instrumentor records the raised exception),
    but nothing marks them as attempts of the same logical call. This hook
    adds an `llm.retry` event to the enclosing span (sim_agent / phase span)
    with the attempt number and error class, so the trace shows exactly when
    a call degraded into backoff and why."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    log.warning(
        f"Gemini retry — attempt {retry_state.attempt_number} failed: "
        f"{str(exc)[:200]}"
    )
    if _otel_trace is None:
        return
    span = _otel_trace.get_current_span()
    if span.is_recording():
        span.add_event("llm.retry", attributes={
            "retry.attempt_number": retry_state.attempt_number,
            "retry.error": str(exc)[:300],
            "retry.is_capacity_error": bool(exc and _is_capacity_error(exc)),
        })


@retry(
    retry=retry_if_not_exception_type(ConfigError),
    stop=stop_after_attempt(6),
    wait=_wait_capacity_aware,
    before_sleep=_record_retry,
    reraise=True,
)
async def generate(
    *,
    model: str,
    prompt: str,
    images: list[bytes] | None = None,
    response_schema: dict | None = None,
    temperature: float = 0.2,
) -> dict | str:
    """Make a Gemini call with rate limiting + retries.

    Returns a dict if the response is JSON, else the raw text. If
    response_schema is given, we instruct the model to emit JSON and parse it.
    """
    minute_bucket, day_bucket = _get_buckets(model)
    await minute_bucket.acquire()
    await day_bucket.acquire()

    client = get_client()

    parts: list[Any] = [prompt]
    if images:
        for img_bytes in images:
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json" if response_schema else "text/plain",
    )

    # Run the sync SDK call in a thread to keep our async loop free. Wrap in a
    # timeout so a stalled response raises (and tenacity retries) instead of
    # blocking the task indefinitely — the SDK call itself sets no socket timeout.
    response = await asyncio.wait_for(
        asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=parts,
            config=config,
        ),
        timeout=_REQUEST_TIMEOUT_S,
    )

    text = response.text or ""
    if response_schema is None:
        return text

    # Try to parse JSON
    cleaned = _strip_json_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.warning(f"Failed to parse JSON from {model}: {e}\nText: {text[:500]}")
        # Fallback: ask Gemini to fix its own JSON (one more call, worth it)
        fix_response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=MODEL_FLASH_LITE,
                contents=[
                    f"Fix this to valid JSON. Return ONLY the JSON object, no prose:\n{text[:2000]}"
                ],
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            ),
            timeout=_REQUEST_TIMEOUT_S,
        )
        return json.loads(_strip_json_fences(fix_response.text or "{}"))
