"""Tests for the OTel noise filter — simab/integrations/phoenix.py.

ADK's native tracing and OpenInference's GoogleGenAIInstrumentor both wrap the
same streaming Gemini calls; OTel logs harmless-but-loud "Failed to detach
context" tracebacks when their context tokens cross async-generator boundaries.
We keep BOTH span sources (the demo wants agent spans AND pipeline spans in
Phoenix) and drop only the noise.
"""
import logging
from types import SimpleNamespace

from simab.integrations.phoenix import _install_otel_noise_filter, pipeline_span
from simab.integrations.session import mark_session_success, run_session
from simab.llm import _record_retry


def _record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="opentelemetry.context", level=logging.ERROR,
        pathname=__file__, lineno=1, msg=msg, args=(), exc_info=None,
    )


def test_filter_drops_context_detach_noise():
    _install_otel_noise_filter()
    otel_logger = logging.getLogger("opentelemetry.context")
    assert not otel_logger.filter(_record("Failed to detach context"))


def test_filter_keeps_other_errors():
    _install_otel_noise_filter()
    otel_logger = logging.getLogger("opentelemetry.context")
    assert otel_logger.filter(_record("exporter crashed for real"))


def test_filter_is_idempotent():
    _install_otel_noise_filter()
    _install_otel_noise_filter()
    otel_logger = logging.getLogger("opentelemetry.context")
    assert len(otel_logger.filters) == 1


def test_pipeline_span_is_safe_without_tracing_backend():
    # Without init_phoenix() the global provider is a no-op — the span context
    # manager must still nest cleanly and never raise.
    with pipeline_span("veratest.run", kind="AGENT", run_id="r1"):
        with pipeline_span("phase.study_designer"):
            pass


def test_pipeline_span_propagates_exceptions():
    try:
        with pipeline_span("phase.cognitive_walkers"):
            raise RuntimeError("quorum failed")
    except RuntimeError as e:
        assert "quorum" in str(e)
    else:
        raise AssertionError("exception was swallowed by pipeline_span")


def test_run_session_yields_span_and_accepts_input_text():
    # With the no-op tracer this yields a NonRecordingSpan; with otel
    # missing it yields None. Either way the contract is "yields something
    # mark_session_success can take" and input_text must not raise.
    with run_session("r1", input_text="Goal: convert\nAudience: founders") as span:
        mark_session_success(span, "Directional winner: variant_a")


def test_mark_session_success_is_safe_without_span():
    mark_session_success(None, "anything")
    mark_session_success(None)


def test_session_output_summarises_synthesis():
    import asyncio
    from unittest.mock import AsyncMock, patch

    from simab.models import Run, Synthesis
    from simab.pipeline import _session_input, _session_output

    run = Run(
        run_id="r1", goal="sign up", audience_raw="founders",
        variant_a_path="a.png", variant_b_path=None,
        synthesis=Synthesis(
            directional_winner="tie",
            cohort_resonance_overall={"variant_a": 6.06, "variant_b": 0.0},
            recommendation="Trim the form.",
        ),
    )
    with patch("simab.pipeline.state.get_run", new=AsyncMock(return_value=run)):
        inp = asyncio.run(_session_input("r1"))
        out = asyncio.run(_session_output("r1"))
    assert "Goal: sign up" in inp and "single-screen" in inp
    assert "tie" in out and "variant_a=6.1/10" in out and "Trim the form." in out
    assert "variant_b" not in out  # zero scores are noise, not signal


def _retry_state(exc: Exception, attempt: int = 2):
    return SimpleNamespace(
        attempt_number=attempt,
        outcome=SimpleNamespace(exception=lambda: exc),
    )


def test_record_retry_is_safe_without_active_span():
    _record_retry(_retry_state(RuntimeError("503 The model is overloaded")))


def test_record_retry_handles_missing_outcome():
    _record_retry(SimpleNamespace(attempt_number=1, outcome=None))
