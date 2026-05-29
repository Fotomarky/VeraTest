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
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from google import genai
from google.genai import types

from .config import CONFIG

log = logging.getLogger(__name__)


# Model identifiers — pick the cheapest model that does the job
MODEL_FLASH_LITE = "gemini-2.5-flash-lite"  # workhorse for sim agents
MODEL_FLASH = "gemini-2.5-flash"            # normalizer, scenario builder
MODEL_PRO = "gemini-2.5-pro"                # auditor, synthesizer (used twice/run)


@dataclass
class RateLimit:
    rpm: int  # requests per minute
    rpd: int  # requests per day


# Conservative limits — leave headroom for retries
_LIMITS = {
    MODEL_FLASH_LITE: RateLimit(rpm=25, rpd=1400),  # cap below quota
    MODEL_FLASH: RateLimit(rpm=12, rpd=480),
    MODEL_PRO: RateLimit(rpm=4, rpd=45),
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


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not CONFIG.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/app/apikey"
            )
        _client = genai.Client(api_key=CONFIG.gemini_api_key)
    return _client


def _strip_json_fences(text: str) -> str:
    """Gemini sometimes wraps JSON in ```json ... ``` fences."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=2, min=5, max=60),
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

    # Run the sync SDK call in a thread to keep our async loop free
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=parts,
        config=config,
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
        fix_response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_FLASH_LITE,
            contents=[
                f"Fix this to valid JSON. Return ONLY the JSON object, no prose:\n{text[:2000]}"
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        return json.loads(_strip_json_fences(fix_response.text or "{}"))
