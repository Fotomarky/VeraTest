"""
Tests for simab/ratelimit.py

Run with: pytest tests/test_ratelimit.py -v
No API calls, no network, no fixtures needed.
"""

import os
import time

import pytest

# Set env vars BEFORE importing the module so the frozen dataclass picks them up.
os.environ["SIMAB_DAILY_RUN_CAP"] = "5"
os.environ["SIMAB_PER_IP_HOUR_CAP"] = "2"
os.environ["SIMAB_MAX_PENDING"] = "3"
os.environ["SIMAB_MAX_UPLOAD_MB"] = "2"
os.environ["SIMAB_ACCESS_CODE"] = ""

import simab.ratelimit as rl

rl._cfg = rl.RateLimitConfig()  # re-read env vars


@pytest.fixture(autouse=True)
def fresh_counters():
    """Reset counters before every test."""
    rl.counters = rl._Counters()
    yield


# ---------------------------------------------------------------------------
# Global daily cap
# ---------------------------------------------------------------------------

class TestDailyCap:
    def test_allows_under_cap(self):
        allowed, remaining = rl.counters.check_daily()
        assert allowed is True
        assert remaining == 5

    def test_blocks_at_cap(self):
        for _ in range(5):
            rl.counters.record_run("1.2.3.4")
        allowed, remaining = rl.counters.check_daily()
        assert allowed is False
        assert remaining == 0

    def test_remaining_decrements(self):
        rl.counters.record_run("1.2.3.4")
        rl.counters.record_run("5.6.7.8")
        _, remaining = rl.counters.check_daily()
        assert remaining == 3

    def test_resets_after_midnight(self):
        for _ in range(5):
            rl.counters.record_run("1.2.3.4")
        rl.counters.daily_reset_at = time.time() - 1
        allowed, remaining = rl.counters.check_daily()
        assert allowed is True
        assert remaining == 5


# ---------------------------------------------------------------------------
# Per-IP hourly cap
# ---------------------------------------------------------------------------

class TestPerIpCap:
    def test_allows_first_request(self):
        allowed, remaining = rl.counters.check_ip("10.0.0.1")
        assert allowed is True
        assert remaining == 2

    def test_blocks_after_cap(self):
        rl.counters.record_run("10.0.0.1")
        rl.counters.record_run("10.0.0.1")
        allowed, _ = rl.counters.check_ip("10.0.0.1")
        assert allowed is False

    def test_different_ips_independent(self):
        rl.counters.record_run("10.0.0.1")
        rl.counters.record_run("10.0.0.1")
        allowed, remaining = rl.counters.check_ip("10.0.0.2")
        assert allowed is True
        assert remaining == 2

    def test_old_timestamps_pruned(self):
        old_time = time.time() - 7200
        rl.counters.ip_timestamps["10.0.0.1"] = [old_time, old_time + 1]
        allowed, remaining = rl.counters.check_ip("10.0.0.1")
        assert allowed is True
        assert remaining == 2


# ---------------------------------------------------------------------------
# Pending queue depth
# ---------------------------------------------------------------------------

class TestPendingQueue:
    def test_allows_under_limit(self):
        assert rl.counters.check_pending() is True

    def test_blocks_at_limit(self):
        for _ in range(3):
            rl.counters.record_run("1.2.3.4")
        assert rl.counters.check_pending() is False

    def test_unblocks_after_finish(self):
        for _ in range(3):
            rl.counters.record_run("1.2.3.4")
        assert rl.counters.check_pending() is False
        rl.notify_run_finished()
        assert rl.counters.check_pending() is True

    def test_finish_never_goes_negative(self):
        rl.notify_run_finished()
        rl.notify_run_finished()
        assert rl.counters.pending_count == 0


# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------

class TestConfig:
    def test_reads_env_vars(self):
        assert rl._cfg.daily_run_cap == 5
        assert rl._cfg.per_ip_hour_cap == 2
        assert rl._cfg.max_pending == 3
        assert rl._cfg.max_upload_bytes == 2 * 1024 * 1024

    def test_access_code_empty_means_disabled(self):
        assert rl._cfg.access_code == ""
