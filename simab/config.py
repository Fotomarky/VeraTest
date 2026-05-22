"""Configuration loaded from environment variables."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    db_path: str
    upload_dir: str
    phoenix_endpoint: str | None
    frontend_url: str
    sim_concurrency: int
    num_agents: int
    ga4_client_id: str | None
    ga4_client_secret: str | None
    ga4_redirect_uri: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            db_path=os.environ.get("SIMAB_DB_PATH", "./simab.db"),
            upload_dir=os.environ.get("SIMAB_UPLOAD_DIR", "./uploads"),
            phoenix_endpoint=os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or None,
            frontend_url=os.environ.get("FRONTEND_URL", "http://localhost:3000"),
            sim_concurrency=int(os.environ.get("SIMAB_SIM_CONCURRENCY", "6")),
            num_agents=int(os.environ.get("SIMAB_NUM_AGENTS", "20")),
            ga4_client_id=os.environ.get("GA4_CLIENT_ID") or None,
            ga4_client_secret=os.environ.get("GA4_CLIENT_SECRET") or None,
            ga4_redirect_uri=os.environ.get(
                "GA4_REDIRECT_URI", "http://localhost:8000/oauth/ga4/callback"
            ),
        )


CONFIG = Config.from_env()
