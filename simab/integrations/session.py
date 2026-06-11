"""OpenTelemetry session wrapper for a single pipeline run.

Phoenix surfaces sessions in its UI as a single grouping of all spans for
one logical workflow — i.e. all ~24 Gemini calls of one VeraTest run.
Wrapping the pipeline in one session span makes the trace view in Phoenix
show one Session per run with all spans nested, vs a flat span list.

Safely no-op when opentelemetry isn't installed (tests, free-tier deploys
without the phoenix extra).
"""
from __future__ import annotations
import contextlib
import logging

log = logging.getLogger(__name__)


@contextlib.contextmanager
def run_session(run_id: str, input_text: str | None = None):
    """Wrap one pipeline run in a Phoenix session span.

    The `openinference.session.id` attribute is what Phoenix's UI uses to
    group spans into Sessions. We set both that and a plain `veratest.run_id`
    so the same span is filterable from either side.

    `input.value` is the OpenInference attribute Phoenix's trace table reads
    for its "input" column — without it the run root renders as "--".
    Yields the span (or None when opentelemetry isn't installed) so the
    caller can hand it to `mark_session_success` on completion.
    """
    try:
        from opentelemetry import trace
    except ImportError:
        log.debug("opentelemetry not installed — session span skipped")
        yield None
        return

    attributes = {
        "openinference.session.id": run_id,
        "openinference.span.kind": "AGENT",
        "veratest.run_id": run_id,
    }
    if input_text:
        attributes["input.value"] = input_text
        attributes["input.mime_type"] = "text/plain"

    tracer = trace.get_tracer("simab.pipeline")
    with tracer.start_as_current_span(
        name=f"veratest_run.{run_id}",
        attributes=attributes,
    ) as span:
        yield span


def mark_session_success(span, output_text: str | None = None) -> None:
    """Set `output.value` and an OK status on the run root span.

    OTel spans default to UNSET, which Phoenix renders as a grey "Unset"
    status; phases that raise are already marked ERROR by the context
    manager, so OK here makes successful runs read green at a glance.
    No-op (never raises) when tracing is off or the span is None.
    """
    if span is None:
        return
    try:
        from opentelemetry.trace import Status, StatusCode

        if output_text:
            span.set_attribute("output.value", output_text)
            span.set_attribute("output.mime_type", "text/plain")
        span.set_status(Status(StatusCode.OK))
    except Exception as e:  # observability must never break the pipeline
        log.debug(f"mark_session_success skipped: {e}")
