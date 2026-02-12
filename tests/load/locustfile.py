"""
Heracles — Enterprise Load Testing Suite
==========================================

Entry point for Locust load tests.
Locust auto-discovers HttpUser subclasses from the imports below.

Usage:
  # Web UI (default) — http://localhost:8089
  cd tests/load && locust

  # With class picker (select personas from the UI)
  cd tests/load && locust --class-picker

  # Autostart with Web UI (starts immediately, UI stays open)
  cd tests/load && locust --autostart --autoquit 10

  # Headless — enterprise scale
  cd tests/load && locust --headless -u 200 -r 10 -t 5m

  # Run only specific tags
  cd tests/load && locust --headless -u 50 -t 1m --tags users posix

  # Debug a single user (no Locust runtime)
  cd tests/load && python locustfile.py

Configuration:
  Settings are loaded from locust.conf in this directory.
  Override any value via CLI flags or LOCUST_* environment variables.
  See: https://docs.locust.io/en/stable/configuration.html
"""

import logging
from datetime import datetime, timezone

from locust import events
from locust.runners import MasterRunner, WorkerRunner

# ── User personas (auto-discovered by Locust) ──────────────────────────────
from users.admin import HeraclesAdminUser  # noqa: F401
from users.readonly import HeraclesReadOnlyUser  # noqa: F401
from users.api_consumer import HeraclesAPIConsumer  # noqa: F401

# ── Load shapes (selectable from UI with --class-picker) ───────────────────
from shapes.enterprise import (  # noqa: F401
    EnterpriseRampShape,
    SpikeTestShape,
    SoakTestShape,
)

logger = logging.getLogger("heracles.loadtest")


# ── Event hooks ────────────────────────────────────────────────────────────

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Called when each Locust process starts. Log runner type."""
    if isinstance(environment.runner, MasterRunner):
        logger.info("Heracles load test — master node initialized")
    elif isinstance(environment.runner, WorkerRunner):
        logger.info("Heracles load test — worker node initialized")
    else:
        logger.info("Heracles load test — standalone mode initialized")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when a test run starts."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    user_count = environment.runner.target_user_count if environment.runner else "?"
    logger.info(
        "══════════════════════════════════════════════════════════════\n"
        "  HERACLES LOAD TEST STARTED\n"
        "  Time:   %s\n"
        "  Host:   %s\n"
        "  Users:  %s\n"
        "══════════════════════════════════════════════════════════════",
        ts, environment.host, user_count,
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when a test run stops. Print summary."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    stats = environment.runner.stats.total if environment.runner else None
    if stats:
        logger.info(
            "══════════════════════════════════════════════════════════════\n"
            "  HERACLES LOAD TEST COMPLETED\n"
            "  Time:       %s\n"
            "  Requests:   %d total, %d failures (%.1f%%)\n"
            "  RPS:        %.1f req/s\n"
            "  Latency:    p50=%dms  p95=%dms  p99=%dms\n"
            "══════════════════════════════════════════════════════════════",
            ts,
            stats.num_requests,
            stats.num_failures,
            (stats.num_failures / stats.num_requests * 100) if stats.num_requests else 0,
            stats.total_rps,
            stats.get_response_time_percentile(0.50) or 0,
            stats.get_response_time_percentile(0.95) or 0,
            stats.get_response_time_percentile(0.99) or 0,
        )
    else:
        logger.info("Heracles load test stopped at %s", ts)


# ── Debug support ──────────────────────────────────────────────────────────
# Run directly: python locustfile.py
# This launches a single user with request logging — no full Locust runtime.
if __name__ == "__main__":
    from locust import run_single_user
    run_single_user(HeraclesAdminUser)
