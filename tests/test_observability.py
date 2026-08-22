"""
Tests for the PHI-safe observability helpers (preconsult/core/observability.py).

The helpers must emit only metadata (event name, request id, counts, timings)
and never health data. These tests lock that boundary: raw PHI-ish strings
passed as metadata are length/type-truncated or must not be logged at all.
"""

import asyncio
import logging

import pytest

from preconsult.core.observability import new_request_id, log_event, timed


def test_new_request_id_is_short_unique_urlsafe():
    a = new_request_id()
    b = new_request_id()
    assert a != b
    assert len(a) <= 16
    # url-safe base64 chars only, no '+'/'/' padding junk (PHI-free token)
    assert all(c.isalnum() or c in "-_" for c in a)


def test_log_event_emits_structured_metadata(caplog):
    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(logging.INFO, "session.init.ok", request_id="abc", lang="en", qa_n=3)
    assert any("event=session.init.ok" in r.message for r in caplog.records)
    assert any("request_id='abc'" in r.message for r in caplog.records)
    assert any("lang='en'" in r.message for r in caplog.records)
    assert any("qa_n=3" in r.message for r in caplog.records)


def test_log_event_truncates_and_quotes_long_values(caplog):
    # A long value (e.g. a free-text length) is truncated to 120 chars to keep
    # the log readable and injection-free.
    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        log_event(logging.INFO, "test", note="x" * 300)
    msg = next(r.message for r in caplog.records if "event=test" in r.message)
    assert "'xxx" in msg
    assert "xxx" * 100 not in msg  # not the full 300-char value


def test_log_event_swallows_errors_never_raises(caplog):
    # Metadata values that fail to serialize must not break the request path.
    class Evil:
        def __str__(self):
            raise ValueError("no str")

    log_event(logging.INFO, "test.resilient", bad=Evil())  # must not raise


@pytest.mark.asyncio
async def test_timed_emits_info_on_success(caplog):
    with caplog.at_level(logging.INFO, logger="preconsult.observability"):
        async with timed("pdf.generate", request_id="rid", lang="en"):
            await asyncio.sleep(0)

    assert any(
        "event=pdf.generate" in r.message and "duration_ms=" in r.message
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_timed_emits_error_event_and_reraises(caplog):
    with caplog.at_level(logging.ERROR, logger="preconsult.observability"):
        with pytest.raises(RuntimeError):
            async with timed("session.init", request_id="rid"):
                raise RuntimeError("down")

    assert any(
        "event=session.init.error" in r.message and "error_type='RuntimeError'" in r.message
        for r in caplog.records
    )
