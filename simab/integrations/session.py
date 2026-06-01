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
def run_session(run_id: str):
    """Wrap one pipeline run in a Phoenix session span.

    The `openinference.session.id` attribute is what Phoenix's UI uses to
    group spans into Sessions. We set both that and a plain `veratest.run_id`
    so the same span is filterable from either side.
    """
    try:
        from opentelemetry import trace
    except ImportError:
        log.debug("opentelemetry not installed — session span skipped")
        yield
        return

    tracer = trace.get_tracer("simab.pipeline")
    with tracer.start_as_current_span(
        name=f"veratest_run.{run_id}",
        attributes={
            "openinference.session.id": run_id,
            "veratest.run_id": run_id,
        },
    ):
        yield
