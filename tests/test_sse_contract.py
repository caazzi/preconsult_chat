"""
SSE wire-contract tests.

Pins the exact streaming format exchanged between the FastAPI endpoints
(``/api/interview-questions-stream`` and ``/api/initial-questions-stream``)
and the Reflex frontend consumer in ``state.py``.

The contract is deliberately strict because a silent drift between the two
sides manifests as a subtle production failure:
  - the endpoint emits ``data: <json.dumps(chunk)>\\n\\n`` (one line);
  - the client parses with ``line.startswith("data: ")`` then
    ``json.loads(line[len("data: "):])``.
"""

import json

import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import patch, AsyncMock

from reflex_app.preconsult.preconsult import api as app

HEADERS = {"X-API-KEY": "ci_test_key_123"}


def _lines(text: str) -> list[str]:
    """Return the non-empty lines of an SSE body (split on real newlines)."""
    return [ln for ln in text.split("\n") if ln]


def _json_payload(line: str) -> str:
    """Mirror state.py's exact consumer: strip 'data: ' prefix and json.loads."""
    assert line.startswith("data: "), f"expected 'data: ' prefix, got {line!r}"
    return json.loads(line[len("data: "):])


async def _collect(body: str) -> str:
    """Replay an SSE body through the real httpx consumer used by state.py."""
    out = ""
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))) as client:
        async with client.stream("POST", "http://test/x") as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    out += json.loads(line[len("data: "):])
    return out


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.update_session", new_callable=AsyncMock)
async def test_stream_emits_json_encoded_string_chunks(mock_update, mock_chain, mock_rate, mock_get, mock_stream):
    """Each chunk is emitted as ``data: <JSON-encoded string>`` on its own line."""
    mock_get.return_value = {"lang": "en", "chief_complaint": "pain"}
    mock_rate.return_value = True

    async def gen():
        yield "Hello\nworld"  # must be JSON-encoded as a single string value

    mock_stream.side_effect = lambda *a, **k: gen()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/api/initial-questions-stream",
            json={"session_id": "x", "chief_complaint": "pain"}, headers=HEADERS,
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            body = "".join([line async for line in response.aiter_text()])

    lines = _lines(body)
    assert lines, "expected at least one SSE event"
    assert len(lines) == 1  # single chunk, single line, no stray blank empty-data

    # the single line is `data: <json>` and the JSON decodes to the exact string
    decoded = _json_payload(lines[0])
    assert decoded == "Hello\nworld"


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.update_session", new_callable=AsyncMock)
async def test_streamed_body_round_trips_through_client_consumer(mock_update, mock_chain, mock_rate, mock_get, mock_stream):
    """The real httpx consumer used by state.py reassembles chunks into the buffer."""
    mock_get.return_value = {"lang": "en", "chief_complaint": "pain"}
    mock_rate.return_value = True

    chunks = ["1. First?", " ", "2. Second?"]

    async def agen():
        for c in chunks:
            yield c

    mock_stream.side_effect = lambda *a, **k: agen()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/api/initial-questions-stream",
            json={"session_id": "x", "chief_complaint": "pain"}, headers=HEADERS,
        ) as response:
            body = "".join([line async for line in response.aiter_text()])

    reassembled = await _collect(body)
    assert reassembled == "1. First? 2. Second?"


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.update_session", new_callable=AsyncMock)
async def test_stream_error_token_is_emitted_and_client_visible(mock_update, mock_chain, mock_rate, mock_get, mock_stream):
    """On a mid-stream error the endpoint must still send one valid event."""
    mock_get.return_value = {"lang": "en", "chief_complaint": "pain"}
    mock_rate.return_value = True

    async def gen():
        yield "partial chunk"
        raise RuntimeError("vertex AI down")

    mock_stream.side_effect = lambda *a, **k: gen()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/api/initial-questions-stream",
            json={"session_id": "x", "chief_complaint": "pain"}, headers=HEADERS,
        ) as response:
            assert response.status_code == 200  # stream resolves 200 even on error
            body = "".join([line async for line in response.aiter_text()])

    # the final data event carries the localized error token (the exception is
    # caught server-side and served as a normal SSE event)
    decoded_lines = [_json_payload(ln) for ln in _lines(body)]
    assert any("Service temporarily unavailable" in d for d in decoded_lines)
    assert "vertex AI down" not in body  # server internals never leak
