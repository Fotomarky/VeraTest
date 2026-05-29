"""
Rate-limiting middleware for VeraTest.

Five layers of protection — each independent, all cheap:

1. Global daily run cap          (SIMAB_DAILY_RUN_CAP, default 50)
2. Per-IP hourly run cap         (SIMAB_PER_IP_HOUR_CAP, default 3)
3. Pending-queue depth limit     (SIMAB_MAX_PENDING, default 5)
4. Upload size limit             (SIMAB_MAX_UPLOAD_MB, default 5)
5. Optional access code          (SIMAB_ACCESS_CODE, default "" = disabled)

All limits are only enforced on POST /api/runs — the endpoint that
burns Gemini credits. Everything else (GET, SSE, share pages) is
unrestricted.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse


# ---------------------------------------------------------------------------
# Configuration (reads from env, sensible hackathon defaults)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RateLimitConfig:
    daily_run_cap: int = int(os.getenv("SIMAB_DAILY_RUN_CAP", "50"))
    per_ip_hour_cap: int = int(os.getenv("SIMAB_PER_IP_HOUR_CAP", "3"))
    max_pending: int = int(os.getenv("SIMAB_MAX_PENDING", "5"))
    max_upload_bytes: int = int(os.getenv("SIMAB_MAX_UPLOAD_MB", "5")) * 1024 * 1024
    access_code: str = os.getenv("SIMAB_ACCESS_CODE", "")  # "" = disabled


_cfg = RateLimitConfig()


# ---------------------------------------------------------------------------
# In-memory counters (resets on redeploy — fine for Cloud Run)
# ---------------------------------------------------------------------------

class _Counters:
    """Simple in-memory counters. No Redis, no extra infra."""

    def __init__(self) -> None:
        self.daily_count: int = 0
        self.daily_reset_at: float = self._next_midnight()
        self.ip_timestamps: dict[str, list[float]] = defaultdict(list)
        self.pending_count: int = 0

    @staticmethod
    def _next_midnight() -> float:
        """Seconds since epoch for the next UTC midnight."""
        now = time.time()
        return now - (now % 86400) + 86400

    def _maybe_reset_daily(self) -> None:
        now = time.time()
        if now >= self.daily_reset_at:
            self.daily_count = 0
            self.daily_reset_at = self._next_midnight()

    def _prune_ip(self, ip: str) -> None:
        """Drop timestamps older than 1 hour."""
        cutoff = time.time() - 3600
        self.ip_timestamps[ip] = [
            t for t in self.ip_timestamps[ip] if t > cutoff
        ]

    def check_daily(self) -> tuple[bool, int]:
        """Returns (allowed, remaining)."""
        self._maybe_reset_daily()
        remaining = max(0, _cfg.daily_run_cap - self.daily_count)
        return self.daily_count < _cfg.daily_run_cap, remaining

    def check_ip(self, ip: str) -> tuple[bool, int]:
        """Returns (allowed, remaining)."""
        self._prune_ip(ip)
        count = len(self.ip_timestamps[ip])
        remaining = max(0, _cfg.per_ip_hour_cap - count)
        return count < _cfg.per_ip_hour_cap, remaining

    def check_pending(self) -> bool:
        return self.pending_count < _cfg.max_pending

    def record_run(self, ip: str) -> None:
        """Call AFTER a run is successfully created."""
        self.daily_count += 1
        self.ip_timestamps[ip].append(time.time())
        self.pending_count += 1

    def run_finished(self) -> None:
        """Call when a run reaches a terminal status (complete/failed)."""
        self.pending_count = max(0, self.pending_count - 1)


counters = _Counters()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def _client_ip(request: Request) -> str:
    """Best-effort client IP, respecting Cloud Run's X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces rate limits on POST /api/runs only.
    Returns 429 with a JSON body explaining which limit was hit.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method != "POST" or request.url.path != "/api/runs":
            return await call_next(request)

        ip = _client_ip(request)

        # Layer 0: access code (if configured)
        if _cfg.access_code:
            code = request.query_params.get("code", "")
            header_code = request.headers.get("x-access-code", "")
            if code != _cfg.access_code and header_code != _cfg.access_code:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "access_code_required",
                        "message": (
                            "This demo requires an access code. "
                            "Pass it as ?code=... or X-Access-Code header."
                        ),
                    },
                )

        # Layer 1: global daily cap
        allowed, _remaining = counters.check_daily()
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "daily_cap_reached",
                    "message": (
                        f"Daily run limit ({_cfg.daily_run_cap}) reached. "
                        "Try again tomorrow, or self-host with your own Gemini key."
                    ),
                    "limit": _cfg.daily_run_cap,
                    "remaining": 0,
                },
                headers={"Retry-After": "3600"},
            )

        # Layer 2: per-IP hourly cap
        ip_allowed, _ip_remaining = counters.check_ip(ip)
        if not ip_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "ip_rate_limit",
                    "message": (
                        f"You've used your {_cfg.per_ip_hour_cap} runs this hour. "
                        "Please wait before submitting another."
                    ),
                    "limit": _cfg.per_ip_hour_cap,
                    "remaining": 0,
                    "window": "1 hour",
                },
                headers={"Retry-After": "900"},
            )

        # Layer 3: pending queue depth
        if not counters.check_pending():
            return JSONResponse(
                status_code=429,
                content={
                    "error": "queue_full",
                    "message": (
                        f"There are already {_cfg.max_pending} runs in progress. "
                        "Please wait for one to finish."
                    ),
                },
                headers={"Retry-After": "60"},
            )

        # Layer 4: upload size (via Content-Length)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _cfg.max_upload_bytes:
            max_mb = _cfg.max_upload_bytes // (1024 * 1024)
            return JSONResponse(
                status_code=413,
                content={
                    "error": "upload_too_large",
                    "message": f"Upload exceeds {max_mb} MB limit. Resize your images.",
                },
            )

        # All checks passed — let the request through
        response = await call_next(request)

        # Record the run only if the endpoint returned 200/201
        if response.status_code in (200, 201):
            counters.record_run(ip)

        return response


def notify_run_finished() -> None:
    """Decrement the pending counter. Call from pipeline.py on complete/failed."""
    counters.run_finished()
