"""
Lightweight, PHI-safe observability helpers.

PreConsult's hard constraint is *zero data persistence* and no health data in
logs. Every helper here is therefore deliberately conservative:

- It never accepts or serializes user-supplied free text (chief complaint,
  conditions, medications, answers, complaint detail).
- Metadata only: event name, request id, language, latency, status, and
  non-content counters (e.g. length of a free-text field, never the value).

Bundling both the log emitters and the (short) request-id generator here keeps
the logging story consistent across the FastAPI backend and the Starlette host.
"""

import json
import logging
import math
import os
import secrets
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from preconsult.core.config import REPOSITORY_REVISION

log = logging.getLogger("preconsult.observability")

# Third-party (non-JSON) lines keep the familiar gunicorn/uvicorn text shape.
TEXT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# OTel log data model severity table. Values between two levels map to the
# lower severity (e.g. a library's NOTICE=25 is WARNING) rather than inventing
# an off-table number.
_SEVERITY_BY_LEVEL = {
    logging.DEBUG: ("DEBUG", 5),
    logging.INFO: ("INFO", 9),
    logging.WARNING: ("WARNING", 13),
    logging.ERROR: ("ERROR", 17),
    logging.CRITICAL: ("CRITICAL", 21),
}


def _severity(level: int) -> tuple[str, int]:
    mapped = _SEVERITY_BY_LEVEL.get(level)
    if mapped is not None:
        return mapped
    if level >= logging.CRITICAL:
        return _SEVERITY_BY_LEVEL[logging.CRITICAL]
    if level >= logging.ERROR:
        return _SEVERITY_BY_LEVEL[logging.ERROR]
    if level >= logging.WARNING:
        return _SEVERITY_BY_LEVEL[logging.WARNING]
    if level >= logging.INFO:
        return _SEVERITY_BY_LEVEL[logging.INFO]
    return _SEVERITY_BY_LEVEL[logging.DEBUG]


# Constant per process: every Lambda sandbox is a new process, so the random
# instance id makes cold-start frequency queryable later. It carries no user
# or host information.
_SERVICE_INSTANCE_ID = secrets.token_hex(4)
_DEPLOYMENT_ENVIRONMENT = os.environ.get("ENV") or "production"

_RESOURCE = {
    "service.name": "preconsult",
    "service.version": REPOSITORY_REVISION,
    "deployment.environment.name": _DEPLOYMENT_ENVIRONMENT,
    "service.instance.id": _SERVICE_INSTANCE_ID,
}

_MISSING = object()


class JsonLogFormatter(logging.Formatter):
    """Render structured events as pure JSON and everything else as text.

    ``log_event`` writes its JSON in ``record.msg``. A Formatter cannot know
    which records are ours, so the message itself is the signal: lines that
    start with ``{`` pass through untouched (one JSON object per line), while
    library/handler lines keep ``TEXT_LOG_FORMAT``. This keeps our stdout
    parseable without making uvicorn/gunicorn output unreadable.
    """

    def __init__(self) -> None:
        super().__init__(fmt=TEXT_LOG_FORMAT)

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, str) and record.msg.startswith("{"):
            return record.getMessage()
        return super().format(record)


def install_log_formatter() -> None:
    """Apply :class:`JsonLogFormatter` to the root handlers.

    Called by ``preconsult.main`` after ``logging.basicConfig``. Re-applying is
    harmless, and iterating (instead of passing ``handlers=``) still works when
    a server or test runner configured the root logger first.
    """
    formatter = JsonLogFormatter()
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)


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


def record_funnel_step(event: str) -> None:
    """Count one anonymous funnel step and emit its structured log line.

    Pre-session steps (landing -> history) happen before the session exists, so
    they can never be keyed by session. They are counted in RAM — exposed read-only
    at ``GET /health/metrics`` as ``funnel.<event>`` — and emitted as one log line
    for persistent history, deliberately without a Redis write: Redis is reserved
    for real patient sessions. Both artefacts are PHI-free (a stable event name
    and a counter, nothing else).
    """
    _inc(f"funnel.{event}")
    log_event(logging.INFO, "funnel.step", step=event)


def record_llm_stream() -> None:
    """Count one attempted LLM stream (``llm.stream.total``).

    A stream that fails mid-flight still counts: the point is that failures stop
    looking like successes in the aggregate, not that only happy paths count.
    """
    _inc("llm.stream.total")


def record_llm_structured_source(source: str | None) -> None:
    """Count how the final question list was obtained.

    ``tool`` -> ``llm.structured.ok`` (the structured output contract held),
    ``text`` -> ``llm.structured.fallback`` (the prose salvage path ran). A
    stream that produced no list at all increments neither. ``source`` is our
    own enum, never user content.
    """
    if source == "tool":
        _inc("llm.structured.ok")
    elif source == "text":
        _inc("llm.structured.fallback")


def record_llm_error(kind: str) -> None:
    """Count one failed LLM stream by stable error kind (``llm.error.<kind>``).

    ``kind`` is the normalized provider vocabulary from ``LLMUpstreamError``
    (``throttled``/``timeout``/``auth``/...) or ``unknown`` for a non-LLM
    exception. It is an enum, never a message or user value.
    """
    _inc(f"llm.error.{kind}")


def new_request_id() -> str:
    """Short, random, correlatable request id (16 chars, URL-safe, no PHI)."""
    return secrets.token_urlsafe(9)


def _sanitize(value: Any) -> Any:
    """Return a JSON-safe scalar, or ``_MISSING`` when it must be dropped.

    Only metadata types are accepted: booleans, numbers and short strings.
    Containers and arbitrary objects are dropped rather than serialized with
    ``str()``/``repr()`` — an exception repr can contain request content.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        # NaN/Infinity are not valid RFC 8259 JSON.
        return value if math.isfinite(value) else _MISSING
    if isinstance(value, str):
        # Collapse all whitespace (including newlines) so one event is always
        # exactly one line, then bound the value.
        return " ".join(value.split())[:120]
    return _MISSING


def _timestamp() -> str:
    """UTC RFC3339 timestamp with millisecond precision and a ``Z`` suffix."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def log_event(level: int, event: str, **extra: Any) -> None:
    """Emit exactly one OTel-shaped JSON log line.

    ``event`` is a stable machine-readable name (e.g. ``session.init``); it is
    both the readable ``body`` and ``attributes["event.name"]``. ``extra`` must
    contain only metadata: request_id, lang, duration_ms, status/status_code,
    counts and similar. Do not pass user content.

    The deploy revision lives in ``resource.service.version`` (GIT_SHA/
    K_REVISION) so every line is attributable to a specific build, and the
    per-process ``resource.service.instance.id`` makes cold starts queryable.
    """
    try:
        attributes: dict[str, Any] = {"event.name": event}
        for key, value in extra.items():
            if key == "event.name":
                continue
            sanitized = _sanitize(value)
            if sanitized is not _MISSING:
                attributes[key] = sanitized

        severity_text, severity_number = _severity(level)
        record = {
            "timestamp": _timestamp(),
            "severity_text": severity_text,
            "severity_number": severity_number,
            "body": event,
            "attributes": attributes,
            "resource": _RESOURCE,
        }
        log.log(
            level,
            json.dumps(
                record,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ),
        )
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
