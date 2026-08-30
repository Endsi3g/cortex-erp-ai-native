"""
Distributed per-item reservation lock, implementing the mutation-time
locking strategy from docs/adr/ADR-002-availability-and-concurrency.md:
a short-TTL Redis/Valkey lock per (company, item_code) serializes the
"re-check availability, then flip the transaction state" window so two
concurrent confirmations of the last unit can't both succeed.

NOTE: this connects to Redis/Valkey directly via `frappe.conf.redis_cache`
(the standard Frappe site_config.json key for the cache Redis instance —
see infra/docker/docker-compose.dev.yml's REDIS_CACHE) rather than an
undocumented `frappe.cache()` locking method, since this has not been
exercised against a live Frappe v15 bench in this environment. Verify
Redis connectivity on your bench before relying on this in production.
"""

from contextlib import contextmanager
from typing import Iterator
import time

try:
    import frappe
except ImportError:
    frappe = None

try:
    import redis
except ImportError:
    redis = None

LOCK_TTL_SECONDS = 5
ACQUIRE_TIMEOUT_SECONDS = 3
RETRY_DELAY_SECONDS = 0.1

_redis_client = None


class ReservationLockError(Exception):
    """Raised when the per-item reservation lock cannot be acquired in time."""


def _get_redis_client():
    global _redis_client
    if not redis:
        return None
    if _redis_client is None:
        url = None
        if frappe and getattr(frappe, "conf", None):
            url = frappe.conf.get("redis_cache")
        _redis_client = redis.from_url(url or "redis://localhost:6379/0")
    return _redis_client


@contextmanager
def reservation_lock(company: str, item_code: str) -> Iterator[None]:
    """
    Acquire the (company, item_code) reservation lock for the duration
    of the `with` block.

    If Redis is unavailable (no `redis` package installed, or no live
    Frappe context — e.g. this repo's pure-Python test suite), this
    degrades to a no-op rather than blocking local/unit testing.
    Production deployments MUST have Redis/Valkey reachable for this
    guard to actually prevent double-booking, per ADR-002 — this is a
    concurrency safety net, not optional polish.
    """
    client = _get_redis_client()
    if not client:
        yield
        return

    key = f"rental:lock:item:{company}:{item_code}"
    deadline = time.monotonic() + ACQUIRE_TIMEOUT_SECONDS
    acquired = False
    try:
        while time.monotonic() < deadline:
            if client.set(key, "1", nx=True, ex=LOCK_TTL_SECONDS):
                acquired = True
                break
            time.sleep(RETRY_DELAY_SECONDS)
        if not acquired:
            raise ReservationLockError(
                f"Could not acquire reservation lock for company={company} item_code={item_code} "
                f"within {ACQUIRE_TIMEOUT_SECONDS}s — another operator/agent is confirming this item "
                "concurrently. Retry the request."
            )
        yield
    finally:
        if acquired:
            client.delete(key)
