"""Adapter behaviour: timeouts, retries, and error normalization.

These exercise the plumbing every provider inherits, without touching a vendor
SDK or the network.
"""

import asyncio

import pytest
from langchain_core.messages import AIMessageChunk

from preconsult.core.errors import LLMUpstreamError
from preconsult.core.llm import LLMConfig, _LangChainClient, deltas_from_chunks


def _config(**overrides) -> LLMConfig:
    values = {
        "provider": "test",
        "model": "test-model",
        "region": "test-region",
        "temperature": 0.0,
        "max_tokens": 16,
        "ttft_timeout_s": 1.0,
        "idle_timeout_s": 1.0,
        "max_retries": 0,
    }
    values.update(overrides)
    return LLMConfig(**values)


class _FakeChat:
    """Stands in for a LangChain chat model; each "response" is one stream."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = 0

    def bind_tools(self, tools):
        return self

    async def astream(self, messages):
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        if hasattr(response, "__aiter__"):
            async for chunk in response:
                yield chunk
        else:
            for chunk in response:
                yield chunk


class _Client(_LangChainClient):
    """A provider whose every failure classifies as throttling."""

    provider = "test"

    def __init__(self, config: LLMConfig, chat: _FakeChat) -> None:
        self._chat_to_build = chat
        super().__init__(config)

    def _build(self):
        return self._chat_to_build

    def _kind_of(self, exc: Exception) -> str:
        return "throttled"


async def _yield_then_raise(chunk, exc):
    yield chunk
    raise exc


async def _slow_then_yield(delay: float, chunk):
    await asyncio.sleep(delay)
    yield chunk


async def _gapped_chunks(first, delay: float, second):
    yield first
    await asyncio.sleep(delay)
    yield second


async def test_retries_a_throttled_failure_before_any_output():
    chat = _FakeChat(RuntimeError("throttled"), [AIMessageChunk(content="ok")])
    client = _Client(_config(max_retries=2), chat)

    deltas = [delta async for delta in client.astream([])]

    assert [delta.text for delta in deltas] == ["ok"]
    assert chat.calls == 2


async def test_does_not_retry_after_output_started():
    chat = _FakeChat(
        _yield_then_raise(AIMessageChunk(content="partial"), RuntimeError("boom"))
    )
    client = _Client(_config(max_retries=3), chat)

    received = []
    with pytest.raises(LLMUpstreamError):
        async for delta in client.astream([]):
            received.append(delta)

    assert [delta.text for delta in received] == ["partial"]
    assert chat.calls == 1


async def test_time_to_first_token_budget_is_enforced():
    chat = _FakeChat(_slow_then_yield(0.2, AIMessageChunk(content="late")))
    client = _Client(_config(ttft_timeout_s=0.01), chat)

    with pytest.raises(LLMUpstreamError) as exc_info:
        async for _ in client.astream([]):
            pass

    assert exc_info.value.kind == "timeout"
    assert exc_info.value.retryable is True


async def test_inter_token_idle_budget_is_enforced():
    chat = _FakeChat(
        _gapped_chunks(AIMessageChunk(content="a"), 0.2, AIMessageChunk(content="b"))
    )
    client = _Client(_config(idle_timeout_s=0.01), chat)

    received = []
    with pytest.raises(LLMUpstreamError) as exc_info:
        async for delta in client.astream([]):
            received.append(delta)

    assert [delta.text for delta in received] == ["a"]
    assert exc_info.value.kind == "timeout"


async def test_deltas_from_chunks_accepts_a_plain_list():
    deltas = [
        delta async for delta in deltas_from_chunks([AIMessageChunk(content="x")])
    ]

    assert [delta.text for delta in deltas] == ["x"]


async def test_tool_calls_are_only_emitted_once_complete():
    partial = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {
                "name": "report_questions",
                "args": '{"questions": ["A?',
                "id": "t1",
                "index": 0,
            }
        ],
    )

    deltas = [delta async for delta in deltas_from_chunks([partial])]

    assert deltas == []
