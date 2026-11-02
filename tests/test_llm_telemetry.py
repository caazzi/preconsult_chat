"""Attributable, PHI-free telemetry for every LLM stream.

The contract these tests lock:

* every stream ends with exactly one ``llm.stream`` event whose fields are
  metadata only (provider/model ids, timings, counts, token usage, stop reason,
  error kind) and never user content;
* a failed stream is visible as a failure — a structured SSE ``error`` event
  plus an ``llm.error.<kind>`` counter — instead of looking like a successful
  HTTP 200 with a text event;
* the terminal ``questions`` event records whether it came from the tool call
  or the prose fallback.

They drive the real ``_question_stream`` and the real
``stream_interview_questions``; only the provider client is a fake.
"""

import json
from unittest.mock import patch

import pytest
from langchain_core.prompts import ChatPromptTemplate

from preconsult.api.endpoints import _question_stream, _StreamSession
from preconsult.core.errors import LLMUpstreamError
from preconsult.core.llm import LLMDelta
from preconsult.core.observability import (
    record_llm_error,
    record_llm_stream,
    record_llm_structured_source,
    reset_counters,
    snapshot_counters,
)
from preconsult.services.agent_service import InterviewChain, stream_interview_questions
from tests.fakes import ToolCallingFakeLLM, session_payload

# A value that cannot appear by accident: if telemetry ever serializes session
# content, this assertion fails loudly.
CANARY_COMPLAINT = "ZZZ-CANARY-COMPLAINT"
CANARY_DETAIL = "ZZZ-CANARY-DETAIL"

FAKE_USAGE = {
    "input_tokens": 120,
    "output_tokens": 45,
    "total_tokens": 165,
    "input_token_details": {"cache_read": 30},
}


def _chain(fake: object) -> InterviewChain:
    """An InterviewChain over a one-line prompt.

    ``stream_interview_questions`` passes the full form input dict; only the
    declared template variables are rendered, so this cannot accidentally drop
    a field the service expects.
    """
    prompt = ChatPromptTemplate.from_messages(
        [("human", "Chief complaint: {chief_complaint} Detail: {complaint_detail}")]
    )
    return InterviewChain(prompt, fake)  # type: ignore[arg-type]


def _ctx() -> _StreamSession:
    return _StreamSession(
        session_id="session-canary-1234",
        session_data=session_payload(
            chief_complaint=CANARY_COMPLAINT,
            complaint_detail=CANARY_DETAIL,
            lang="en",
        ),
        lang="en",
        err_msg="⚠️ ERROR: Service temporarily unavailable. Please try again.",
        request_id="req-telemetry",
    )


async def _body(response) -> str:
    return "".join([chunk async for chunk in response.body_iterator])


def _payloads(body: str) -> list:
    return [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def _events(log, name: str) -> list[dict]:
    return [call.kwargs for call in log.call_args_list if call.args[1] == name]


class _FailingChain:
    """Chain stub that streams one text delta and then fails mid-stream."""

    provider = "fake"
    model = "fake-fail"

    def __init__(self, exc: Exception, text: str = "1. Partial?") -> None:
        self._exc = exc
        self._text = text

    async def astream(self, _input_dict: dict):
        if self._text:
            yield LLMDelta(text=self._text)
        raise self._exc


@pytest.fixture(autouse=True)
def _fresh_counters():
    reset_counters()
    yield
    reset_counters()


@pytest.mark.asyncio
async def test_tool_stream_logs_one_phi_free_metadata_event():
    fake = ToolCallingFakeLLM(
        text="1. Question A?\n2. Question B?",
        questions=["Question A?", "Question B?"],
        usage=FAKE_USAGE,
        finish_reason="stop",
    )

    with patch("preconsult.api.endpoints.log_event") as log:
        body = await _body(
            _question_stream(_ctx(), _chain(fake), topic="stream.initial")
        )

    events = _events(log, "llm.stream")
    assert len(events) == 1, "exactly one telemetry event per stream"
    event = events[0]

    # Identity + counts (all metadata).
    assert event["provider"] == "fake"
    assert event["model"] == "fake-vertex"
    assert event["topic"] == "stream.initial"
    assert event["request_id"] == "req-telemetry"
    assert isinstance(event["ttft_ms"], int) and event["ttft_ms"] >= 0
    assert isinstance(event["duration_ms"], int) and event["duration_ms"] >= 0
    assert event["chunks"] == 1
    assert event["structured"] is True
    assert event["fallback"] is False
    assert event["input_tokens"] == 120
    assert event["output_tokens"] == 45
    assert event["cached_tokens"] == 30
    assert event["finish_reason"] == "stop"
    assert event["error_kind"] is None

    # Zero PHI: the canary free text is nowhere in any logged payload.
    serialized = json.dumps(
        [call.kwargs for call in log.call_args_list], default=str, ensure_ascii=False
    )
    assert CANARY_COMPLAINT not in serialized
    assert CANARY_DETAIL not in serialized

    # The structured list still reaches the wire unchanged.
    assert {
        "type": "questions",
        "questions": ["Question A?", "Question B?"],
    } in _payloads(body)

    counters = snapshot_counters()
    assert counters["llm.stream.total"] == 1
    assert counters["llm.structured.ok"] == 1
    assert "llm.structured.fallback" not in counters
    assert not any(key.startswith("llm.error.") for key in counters)


@pytest.mark.asyncio
async def test_prose_fallback_is_counted_as_fallback():
    fake = ToolCallingFakeLLM(
        text="1. Question A?\n2. Question B?",
        finish_reason="end_turn",
    )

    with patch("preconsult.api.endpoints.log_event") as log:
        await _body(_question_stream(_ctx(), _chain(fake), topic="stream.interview"))

    event = _events(log, "llm.stream")[0]
    assert event["structured"] is False
    assert event["fallback"] is True
    assert event["finish_reason"] == "end_turn"
    # The fake reports no usage, so token fields stay absent rather than 0.
    assert event["input_tokens"] is None
    assert event["output_tokens"] is None
    assert event["cached_tokens"] is None

    counters = snapshot_counters()
    assert counters["llm.stream.total"] == 1
    assert counters["llm.structured.fallback"] == 1
    assert "llm.structured.ok" not in counters


@pytest.mark.asyncio
async def test_stream_without_a_list_counts_neither_path():
    fake = ToolCallingFakeLLM(text="Only one line, not a question list.")

    with patch("preconsult.api.endpoints.log_event") as log:
        body = await _body(
            _question_stream(_ctx(), _chain(fake), topic="stream.initial")
        )

    event = _events(log, "llm.stream")[0]
    assert event["structured"] is False
    assert event["fallback"] is False
    assert _payloads(body) == ["Only one line, not a question list."]

    counters = snapshot_counters()
    assert counters["llm.stream.total"] == 1
    assert "llm.structured.ok" not in counters
    assert "llm.structured.fallback" not in counters


@pytest.mark.asyncio
async def test_terminal_questions_event_records_its_source():
    tool_events = [
        event
        async for event in stream_interview_questions(
            session_payload(),
            "en",
            _chain(
                ToolCallingFakeLLM(
                    text="1. Question A?\n2. Question B?",
                    questions=["Question A?", "Question B?"],
                )
            ),
        )
    ]
    assert [e.source for e in tool_events if e.kind == "questions"] == ["tool"]

    text_events = [
        event
        async for event in stream_interview_questions(
            session_payload(),
            "en",
            _chain(ToolCallingFakeLLM(text="1. Question A?\n2. Question B?")),
        )
    ]
    assert [e.source for e in text_events if e.kind == "questions"] == ["text"]


@pytest.mark.asyncio
async def test_throttled_upstream_error_is_visible_and_counted():
    chain = _FailingChain(LLMUpstreamError("throttled", provider="fake"))

    with patch("preconsult.api.endpoints.log_event") as log:
        body = await _body(_question_stream(_ctx(), chain, topic="stream.initial"))

    payloads = _payloads(body)
    assert payloads[0] == "1. Partial?"
    assert payloads[1] == {"type": "error", "code": "llm_unavailable"}
    # Back-compat: the localized text event is still emitted after the code.
    assert "Service temporarily unavailable" in payloads[2]

    event = _events(log, "llm.stream")[0]
    assert event["error_kind"] == "throttled"
    assert event["structured"] is False
    assert event["fallback"] is False
    assert event["chunks"] == 1
    assert isinstance(event["ttft_ms"], int)

    counters = snapshot_counters()
    assert counters["llm.error.throttled"] == 1
    assert counters["llm.stream.total"] == 1


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("timeout", "llm_unavailable"),
        ("auth", "ai_upstream_error"),
        ("invalid_request", "ai_upstream_error"),
        ("upstream", "ai_upstream_error"),
    ],
)
@pytest.mark.asyncio
async def test_upstream_kind_mapping_is_stable(kind, code):
    chain = _FailingChain(LLMUpstreamError(kind, provider="fake"), text="")

    with patch("preconsult.api.endpoints.log_event") as log:
        body = await _body(_question_stream(_ctx(), chain, topic="stream.initial"))

    assert _payloads(body)[0] == {"type": "error", "code": code}
    assert _events(log, "llm.stream")[0]["error_kind"] == kind
    assert snapshot_counters()[f"llm.error.{kind}"] == 1


@pytest.mark.asyncio
async def test_non_llm_exception_maps_to_internal_error_and_unknown_bucket():
    chain = _FailingChain(RuntimeError("unexpected"), text="")

    with patch("preconsult.api.endpoints.log_event") as log:
        body = await _body(_question_stream(_ctx(), chain, topic="stream.interview"))

    assert _payloads(body)[0] == {"type": "error", "code": "internal_error"}
    assert _events(log, "llm.stream")[0]["error_kind"] == "unknown"
    assert _events(log, "stream.interview.error")[0]["error_kind"] == "unknown"
    assert snapshot_counters()["llm.error.unknown"] == 1


def test_counter_helpers_use_stable_metric_names():
    record_llm_stream()
    record_llm_stream()
    record_llm_structured_source("tool")
    record_llm_structured_source("text")
    record_llm_structured_source(None)
    record_llm_error("timeout")

    counters = snapshot_counters()
    assert counters["llm.stream.total"] == 2
    assert counters["llm.structured.ok"] == 1
    assert counters["llm.structured.fallback"] == 1
    assert counters["llm.error.timeout"] == 1


def test_llm_identity_prefers_the_adapter_and_falls_back_to_config():
    from preconsult.api.endpoints import _llm_identity
    from preconsult.core.config import LLM_MODEL, LLM_PROVIDER

    class Adapter:
        provider = "bedrock"
        model = "claude-test"

    assert _llm_identity(Adapter()) == ("bedrock", "claude-test")
    # A chain with no identity (test double / future shape) reports the
    # configured deployment instead of an empty string.
    assert _llm_identity(object()) == (LLM_PROVIDER, LLM_MODEL)
