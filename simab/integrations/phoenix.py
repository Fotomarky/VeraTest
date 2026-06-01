"""Arize Phoenix observability — optional, self-hosted, MIT-licensed.

Phoenix is an open-source LLM observability platform you can run locally
via Docker. We auto-instrument the google-genai SDK so every Gemini call
becomes a span with full inputs/outputs visible in the Phoenix UI.

Run Phoenix locally:
    docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

Then set PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317 in your env.

The dashboard is at http://localhost:6006 — show this in the demo.
"""
from __future__ import annotations
import logging

from ..config import CONFIG

log = logging.getLogger(__name__)

_initialized = False


def init_phoenix() -> bool:
    """Initialize Phoenix tracing if PHOENIX_COLLECTOR_ENDPOINT is set.

    Returns True if successfully initialized, False if skipped.
    Safe to call multiple times.
    """
    global _initialized
    if _initialized:
        return True

    if not CONFIG.phoenix_endpoint:
        log.info("Phoenix not configured (PHOENIX_COLLECTOR_ENDPOINT not set) — skipping")
        return False

    try:
        from phoenix.otel import register
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        register_kwargs = dict(
            project_name=CONFIG.phoenix_project,
            endpoint=CONFIG.phoenix_endpoint,
            auto_instrument=False,
        )
        if CONFIG.phoenix_api_key:
            register_kwargs["headers"] = {"api_key": CONFIG.phoenix_api_key}
        tracer_provider = register(**register_kwargs)
        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        _initialized = True
        log.info(f"Phoenix tracing enabled — UI at http://localhost:6006")
        return True
    except ImportError:
        log.warning(
            "Phoenix not installed. To enable observability, run: "
            "pip install 'simab[phoenix]'"
        )
        return False
    except Exception as e:
        log.warning(f"Phoenix init failed (non-fatal): {e}")
        return False
