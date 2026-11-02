"""
Tests for the PHI-safe observability helpers (preconsult/core/observability.py).

The helpers must emit only metadata (event name, request id, counts, timings)
and never health data. These tests lock that boundary: raw PHI-ish strings
passed as metadata are length/type-truncated or must not be logged at all.

They also lock the OTel-shaped JSON encoding: one object per line, with
``timestamp``/``severity_text``/``severity_number``/``body``/``attributes``/
``resource``. Event names and attribute keys are unchanged from the old text
format, so existing greps and dashboards keep working.
"""

import asyncio
import json
import logging
import os
import re

import pytest

from preconsult.core.observability import (
    JsonLogFormatter,
    log_event,
    new_request_id,
    timed,
)


def _json_lines(caplog) -> list[dict]:
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]


def _event(caplog, name: str) -> dict:
    return next(event for event in _json_lines(caplog) if event["body"] == name)


def test_new_request_id_is_short_unique_urlsafe():
    a = new_request_id()
    b = new_request_id()
    assert a != b
    assert len(a) <= 16
    # url-safe base64 chars only, no '+'/'/' padding junk (PHI-free token)
    assert all(c.isalnum() or c in "-_" for c in a)


def test_log_event_emits_one_otel_shaped_json_object(caplog):
    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(
            logging.INFO,
            "session.init.ok",
            request_id="abc",
            lang="en",
            qa_n=3,
            optional=None,
        )

    records = _json_lines(caplog)
    assert len(records) == 1
    record = records[0]
    assert set(record) == {
        "timestamp",
        "severity_text",
        "severity_number",
        "body",
        "attributes",
        "resource",
    }
    assert record["body"] == "session.init.ok"
    assert record["severity_text"] == "INFO"
    assert record["severity_number"] == 9
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", record["timestamp"]
    )
    # Extra keys are unchanged, metadata-only, and None is omitted.
    assert record["attributes"] == {
        "event.name": "session.init.ok",
        "request_id": "abc",
        "lang": "en",
        "qa_n": 3,
    }


@pytest.mark.parametrize(
    ("level", "severity_text", "severity_number"),
    [
        (logging.DEBUG, "DEBUG", 5),
        (logging.INFO, "INFO", 9),
        (logging.WARNING, "WARNING", 13),
        (logging.ERROR, "ERROR", 17),
        (logging.CRITICAL, "CRITICAL", 21),
    ],
)
def test_severity_mapping(level, severity_text, severity_number, caplog):
    with caplog.at_level(logging.DEBUG, logger="preconsult.observability"):
        log_event(level, "severity.test")

    record = _event(caplog, "severity.test")
    assert record["severity_text"] == severity_text
    assert record["severity_number"] == severity_number


def test_resource_fields_are_constant_and_carry_the_deploy_revision(caplog):
    from preconsult.core.config import REPOSITORY_REVISION

    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(logging.INFO, "resource.first")
        log_event(logging.INFO, "resource.second")

    first = _event(caplog, "resource.first")["resource"]
    second = _event(caplog, "resource.second")["resource"]

    assert first == second
    assert first["service.name"] == "preconsult"
    assert first["service.version"] == REPOSITORY_REVISION
    assert first["deployment.environment.name"] == (
        os.environ.get("ENV") or "production"
    )
    # Eight lowercase hex chars, generated once per process.
    assert re.fullmatch(r"[0-9a-f]{8}", first["service.instance.id"])


def test_attribute_newline_is_collapsed_to_a_single_line(caplog):
    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(logging.INFO, "newline.test", note="line one\nline two")

    record = _event(caplog, "newline.test")
    assert record["attributes"]["note"] == "line one line two"
    raw = caplog.records[-1].getMessage()
    assert "\n" not in raw
    assert len(raw.splitlines()) == 1


def test_long_attribute_is_truncated_to_120_chars_in_json(caplog):
    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(logging.INFO, "truncate.test", note="x" * 300)

    record = _event(caplog, "truncate.test")
    assert record["attributes"]["note"] == "x" * 120


def test_unserialisable_values_are_dropped_without_raising(caplog):
    # An exception repr or arbitrary object dump can contain request content,
    # so unsupported values are dropped instead of stringified.
    class Evil:
        def __str__(self):
            raise ValueError("no str")

    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(
            logging.INFO,
            "test.resilient",
            bad=Evil(),
            mapping={"secret": "nope"},
            ok="kept",
        )

    record = _event(caplog, "test.resilient")
    assert record["attributes"] == {"event.name": "test.resilient", "ok": "kept"}


@pytest.mark.asyncio
async def test_timed_emits_info_on_success(caplog):
    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        async with timed("pdf.generate", request_id="rid", lang="en"):
            await asyncio.sleep(0)

    record = _event(caplog, "pdf.generate")
    assert record["attributes"]["request_id"] == "rid"
    assert record["attributes"]["lang"] == "en"
    assert isinstance(record["attributes"]["duration_ms"], int)


@pytest.mark.asyncio
async def test_timed_emits_error_event_and_reraises(caplog):
    with caplog.at_level(logging.ERROR, logger="preconsult.observability"):
        with pytest.raises(RuntimeError):
            async with timed("session.init", request_id="rid"):
                raise RuntimeError("down")

    record = _event(caplog, "session.init.error")
    assert record["attributes"]["error_type"] == "RuntimeError"
    assert record["severity_text"] == "ERROR"


@pytest.mark.asyncio
async def test_exception_text_and_phi_canary_never_reach_the_json(caplog):
    canary = "ZZZ-CANARY-EXCEPTION-TEXT"

    with caplog.at_level(logging.ERROR, logger="preconsult.observability"):
        with pytest.raises(RuntimeError):
            async with timed("session.init", request_id="rid"):
                raise RuntimeError(canary)

    record = _event(caplog, "session.init.error")
    serialized = json.dumps(record)
    assert canary not in serialized
    assert record["attributes"]["error_type"] == "RuntimeError"


def test_log_event_is_revision_tagged_in_resource(caplog):
    """Every event carries the deploy revision so logs are attributable to a
    specific deployed build (the stale-shell incident was hard to pin to a
    revision before)."""
    from preconsult.core.config import REPOSITORY_REVISION

    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(logging.INFO, "health.probe", request_id="rid")

    record = _event(caplog, "health.probe")
    assert record["resource"]["service.version"] == REPOSITORY_REVISION


def test_formatter_keeps_json_verbatim_and_formats_other_lines_as_text():
    formatter = JsonLogFormatter()

    structured = logging.LogRecord(
        "preconsult.observability",
        logging.INFO,
        __file__,
        1,
        '{"body":"app.boot"}',
        (),
        None,
    )
    assert formatter.format(structured) == '{"body":"app.boot"}'

    library = logging.LogRecord(
        "uvicorn.error",
        logging.INFO,
        __file__,
        1,
        "started %s",
        ("worker",),
        None,
    )
    rendered = formatter.format(library)
    assert re.match(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - INFO - started worker$",
        rendered,
    )


def test_counters_inc_and_snapshot():
    from preconsult.core.observability import _inc, snapshot_counters, reset_counters

    reset_counters()
    _inc("socket.handshake_rejected")
    _inc("socket.handshake_rejected")
    _inc("static.asset_404")
    snap = snapshot_counters()
    assert snap["socket.handshake_rejected"] == 2
    assert snap["static.asset_404"] == 1
    reset_counters()
    assert snapshot_counters() == {}
