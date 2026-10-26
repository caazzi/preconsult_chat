"""Health, readiness and metrics probes (Reflex-free).

These handlers are generic HTTP; they lived in the Reflex host only because
that is where the app was assembled. Keeping them here means the SPA cutover
does not have to rewrite the endpoints the platform and CI depend on.

The single Reflex-shaped input is the interactive event-channel probe. The host
injects it via ``event_channel_probe`` while Reflex owns ``/_event``; after the
cutover nothing sets it and the payload reports ``not_configured`` instead of
claiming a socket path that no longer exists.

``check_redis_health_throttled`` and the probe cache are throttled on purpose:
these endpoints are hit by CI, scanners and Cloud Run readiness polling, and an
unthrottled Redis ping per request would drain the serverless free tier.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

from starlette.responses import JSONResponse

from preconsult.core.config import REPOSITORY_REVISION
from preconsult.core.observability import log_event, new_request_id, snapshot_counters

# Throttle health probes so frequently-hit health endpoints (CI, scanners, and
# Cloud Run readiness polling) do not consume the serverless Redis quota. Value
# is a TTL window in seconds; statuses are recomputed at most once per window and
# otherwise served from the cache. Requires a worker-global lock to avoid thundering
# herd on cold start.
_health_probe_cache: dict[str, tuple[float, str]] = {}
_health_probe_lock = asyncio.Lock()
_HEALTH_PROBE_TTL_S = 60.0

EventChannelProbe = Callable[[], Awaitable[str]]


def _reset_health_probe_cache_unlocked() -> None:
    """Clear the health-probe throttle cache (mainly for deterministic tests)."""
    _health_probe_cache.clear()


async def _throttled_probe(key: str, probe: EventChannelProbe) -> str:
    """Return a cached probe status, refreshing at most once per TTL window.

    ``probe`` is an async callable returning a status string (e.g. ``"ok"``).
    """
    cache_key = f"health:{key}"
    async with _health_probe_lock:
        now = time.monotonic()
        cached = _health_probe_cache.get(cache_key)
        if cached is not None and now - cached[0] < _HEALTH_PROBE_TTL_S:
            return cached[1]
    # Fresh probe outside the lock (still coalesced by the TTL).
    status = await probe()
    async with _health_probe_lock:
        _health_probe_cache[cache_key] = (time.monotonic(), status)
    return status


async def check_redis_health_throttled() -> str:
    """Redis reachability as a throttled status string.

    Returns ``ok`` | ``quota_exceeded`` | ``unavailable`` so an exhausted
    serverless Redis quota is surfaced explicitly rather than as a generic
    outage. Probed at most ~once per minute (see _throttled_probe).
    """
    from preconsult.services.session_service import check_redis_status

    return await _throttled_probe("redis", check_redis_status)


def register_health_routes(app, event_channel_probe: EventChannelProbe | None = None) -> None:
    """Register /health, /health/live, /health/ready and /health/metrics.

    Order is preserved from the monolith: the aggregate endpoint first, then the
    specific ones. ``app`` is any Starlette/FastAPI router or application.

    ``event_channel_probe`` is bound per app rather than stored in a module
    global on purpose: a global would make ``/health`` depend on whether some
    other module had imported the Reflex host, which is exactly the kind of
    order-dependent behaviour that is impossible to debug. Pass it explicitly
    while Reflex owns the socket; leave it out afterwards and the payload says
    ``not_configured``.
    """

    async def event_channel_status() -> str:
        if event_channel_probe is None:
            return "not_configured"
        return await _throttled_probe("event_channel", event_channel_probe)

    async def health_live(request):
        # Liveness: process is up. No external dependency probed so Cloud Run
        # never restarts a healthy-but-slow-to-warm container unnecessarily.
        return JSONResponse({"status": "healthy", "checks": {"live": "ok"}})


    async def health_ready(request):
        # Readiness: only serve traffic when Redis is reachable (sessions and
        # rate limiting depend on it). 503 means "don't send me requests yet".
        # Throttled so readiness polling does not burn the serverless Redis quota.
        redis_status = await check_redis_health_throttled()
        if redis_status != "ok":
            # A distinct code for quota exhaustion so alerts/ops can distinguish
            # "daily quota spent" from a general outage.
            code = (
                "redis_quota_exceeded"
                if redis_status == "quota_exceeded"
                else "service_unavailable"
            )
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "redis": redis_status, "code": code},
            )
        return JSONResponse({"status": "ready", "redis": "ok"})


    async def health(request):
        # Aggregate endpoint retained for backward compatibility with the
        # existing CI smoke test which asserts `redis` is "ok"/"unavailable".
        # It also surfaces the interactive-channel status so ops can confirm the
        # socket path works, not just REST/health. Both probes are throttled so
        # frequently-hit health endpoints don't consume the serverless Redis quota.
        request_id = new_request_id()
        redis_status = await check_redis_health_throttled()
        channel = await event_channel_status()
        log_event(
            logging.INFO,
            "health.probe",
            request_id=request_id,
            redis=redis_status,
            event_channel=channel,
        )
        payload = {
            "status": "healthy",
            "redis": redis_status,
            "event_channel": channel,
        }
        # Provide a stable machine-readable code when storage is unhealthy so
        # alerts/CI can key on quota exhaustion as distinct from a general outage.
        if redis_status == "quota_exceeded":
            payload["code"] = "redis_quota_exceeded"
        elif redis_status == "unavailable":
            payload["code"] = "redis_unavailable"
        return JSONResponse(payload)


    async def health_metrics(request):
        # Read-only, in-memory aggregation of high-signal outcome counters
        # (socket.handshake_rejected, static.asset_404, http.status.*). These are
        # PHI-free (path/status/event-name keys only) and per-worker (in-memory),
        # intended for monitoring/alerting on the stale-shell/socket failure
        # classes, not as a store of truth. Not throttled: it resolves from RAM
        # and never touches Redis.
        return JSONResponse(
            {
                "revision": REPOSITORY_REVISION,
                "counters": snapshot_counters(),
            }
        )



    app.add_route("/health", health, include_in_schema=False, methods=["GET"])
    app.add_route("/health/live", health_live, include_in_schema=False, methods=["GET"])
    app.add_route(
        "/health/ready", health_ready, include_in_schema=False, methods=["GET"]
    )
    app.add_route(
        "/health/metrics", health_metrics, include_in_schema=False, methods=["GET"]
    )
