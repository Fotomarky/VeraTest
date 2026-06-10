#!/usr/bin/env python3
"""Deploy the VeraTest Concierge agent to Vertex AI Agent Engine.

This is the *strongest* "Google Cloud Agent Builder" signal for judging:
the ADK agent in `simab/agent.py` runs as a managed Agent Engine instance
rather than just inside a container. It is the stretch goal — the Cloud Run
path (`adk api_server simab`) is the lean floor. See docs/agent-builder.md.

Prerequisites (you run this locally, where you're authenticated):
    pip install -e ".[agent]"
    gcloud auth application-default login         # ADC
    gcloud config set project veratest-497813
    # A GCS staging bucket must exist (created below if missing requires perms):
    #   gsutil mb -l us-central1 gs://veratest-agent-staging

Usage:
    python scripts/deploy_agent_engine.py \
        --project veratest-497813 \
        --location us-central1 \
        --bucket gs://veratest-agent-staging

Env-var fallbacks: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION,
VERATEST_STAGING_BUCKET, PHOENIX_BASE_URL, PHOENIX_API_KEY.

NOTE: the Agent Engine Python API surface (class names, the create() call,
requirements packaging) shifts between vertexai / google-cloud-aiplatform
releases. This script targets the `vertexai.agent_engines` API. If your
installed version differs, adjust the marked block — the rest is stable.
"""
from __future__ import annotations

import argparse
import os
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Deploy VeraTest Concierge to Agent Engine")
    p.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", "veratest-497813"))
    p.add_argument("--location", default=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))
    p.add_argument(
        "--bucket",
        default=os.environ.get("VERATEST_STAGING_BUCKET", "gs://veratest-agent-staging"),
        help="GCS staging bucket (gs://...). Must already exist.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the agent and print the plan without deploying.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Force Vertex routing for the agent's Gemini calls.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", args.project)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", args.location)

    # Build the agent (import after env is set so Vertex routing applies).
    try:
        from simab.agent import build_root_agent
    except Exception as e:
        print(f"ERROR importing simab.agent: {e}", file=sys.stderr)
        print('Did you run `pip install -e ".[agent]"`?', file=sys.stderr)
        return 1

    root_agent = build_root_agent()
    print(f"Built agent: {root_agent.name}")
    print(f"  project={args.project}  location={args.location}  bucket={args.bucket}")

    if args.dry_run:
        print("[dry-run] Skipping deploy. Agent built successfully.")
        return 0

    # --- Agent Engine deploy (version-sensitive block) --------------------
    try:
        import vertexai
        from vertexai import agent_engines
        from vertexai.preview import reasoning_engines
    except Exception as e:
        print(f"ERROR importing vertexai agent_engines: {e}", file=sys.stderr)
        print("Install with: pip install \"google-cloud-aiplatform[agent-engines]\"", file=sys.stderr)
        return 1

    vertexai.init(project=args.project, location=args.location, staging_bucket=args.bucket)

    # Wrap the ADK agent so Agent Engine can serve it.
    app = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)

    # Runtime env the deployed instance needs (Phoenix MCP target).
    env_vars = {"GOOGLE_GENAI_USE_VERTEXAI": "TRUE"}
    if os.environ.get("PHOENIX_BASE_URL"):
        env_vars["PHOENIX_BASE_URL"] = os.environ["PHOENIX_BASE_URL"]
    if os.environ.get("PHOENIX_API_KEY"):
        env_vars["PHOENIX_API_KEY"] = os.environ["PHOENIX_API_KEY"]

    print("Deploying to Agent Engine (this can take several minutes)...")
    remote_app = agent_engines.create(
        app,
        requirements=[
            "google-adk==1.34.3",
            "google-cloud-aiplatform[agent-engines]==1.156.0",
            "mcp==1.27.2",
            "aiosqlite>=0.20",
            "pydantic>=2.7",
            "pillow>=10.0",
            "tenacity>=8.5",
            "httpx>=0.27",
        ],
        # Ship the local package so the pipeline tools are importable.
        extra_packages=["./simab"],
        env_vars=env_vars,
        display_name="VeraTest Concierge",
        description="Synthetic UX pretest agent — Gemini + ADK + Arize Phoenix MCP.",
    )

    print("\n✅ Deployed.")
    print(f"   Resource name: {remote_app.resource_name}")
    print("   Test it:")
    print(
        "     from vertexai import agent_engines\n"
        f"     a = agent_engines.get('{remote_app.resource_name}')\n"
        "     for e in a.stream_query(message='Pretest tests/fixtures/variant_a.png "
        "for sign-up, audience=founders'): print(e)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
