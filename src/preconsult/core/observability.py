"""
Lightweight, PHI-safe observability helpers.

PreConsult's hard constraint is *zero data persistence* and no health data in
logs. Every helper here is therefore deliberately conservative:

- It never accepts or serializes user-supplied free text (chief complaint,
  conditions, medications, answers, complaint detail).
- Metadata only: event name, request id, language, latency, status, and
  non-content counters (e.g. length of a free-text field, never the value).

Bundling both the log emitters and the (short) request-id generator here keeps
the logging story consistent across the FastAPI backend and the Reflex host.
"""

import logging
import secrets
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

from preconsult.core.config import REPOSITORY_REVISION

log = logging.getLogger("preconsult.observability")


# ---------------------------------------------------------------------------
# In-memory, PHI-safe counters
#
# Aggregate the high-signal,"failure-tell-tale" outcomes that would otherwise be
# buried in log volume and hard to alert on: rejected socket handshakes, missing
# static assets, and non-2xx HTTP outcomes keyed by path+status. These never
# hold user content — only path prefixes / statuses / stable event names — so
# they stay within the zero-PHI guarantee. Exposed read-only via /health/metrics.
# ---------------------------------------------------------------------------
_counter_lock = threading.Lock()
_counters: dict[str, int] = {}


def _inc(name: str, *, n: int = 1) -> None:
    with _counter_lock:
        _counters[name] = _counters.get(name, 0) + n


def snapshot_counters() -> dict[str, int]:
    """Return a copy of the counters. Path/status keyed, PHI-free."""
    with _counter_lock:
        return dict(_counters)


def reset_counters() -> None:
    """Clear all counters (mainly for deterministic tests)."""
    with _counter_lock:
        _counters.clear()


def new_request_id() -> str:
    """Short, random, correlatable request id (16 chars, URL-safe, no PHI)."""
    return secrets.token_urlsafe(9)


def _fmt(extra: dict[str, Any]) -> str:
    # Deterministic, injection-safe "key=value" payload; values are forced to
    # safe JSON-like scalars/short strings by the caller.
    return " ".join(f"{k}={_val(v)}" for k, v in sorted(extra.items()) if v is not None)


def _val(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # collapse whitespace and quote to keep the parse unambiguous
    return repr(s.strip()[:120])


def log_event(level: int, event: str, **extra: Any) -> None:
    """Emit one structured, PHI-safe log line.

    ``event`` is a stable machine-readable name (e.g. ``session.init``).
    ``extra`` must contain only metadata: request_id, lang, duration_ms,
    status/status_code, counts and similar. Do not pass user content.

    Every line is tagged with the deploy ``revision`` (GIT_SHA/K_REVISION) so
    logs are attributable to a specific deployed build. An explicit ``revision``
    in ``extra`` wins (callers can override).
    """
    try:
        meta = dict(extra)
        meta.setdefault("revision", REPOSITORY_REVISION)
        log.log(level, f"event={event} {_fmt(meta)}".strip())
    except Exception:  # logging must never break the request path
        pass


@asynccontextmanager
async def timed(event: str, *, request_id: str, **metadata: Any):
    """Time a coroutine body and emit one event line, PHI-safe.

    Usage::

        async with timed("session.init", request_id=rid, lang=lang):
            ...
    """
    start = time.monotonic()
    try:
        yield
    except Exception as exc:
        log_event(
            logging.ERROR,
            f"{event}.error",
            request_id=request_id,
            duration_ms=int((time.monotonic() - start) * 1000),
            error_type=type(exc).__name__,
            **metadata,
        )
        raise
    else:
        log_event(
            logging.INFO,
            event,
            request_id=request_id,
            duration_ms=int((time.monotonic() - start) * 1000),
            **metadata,
        )
