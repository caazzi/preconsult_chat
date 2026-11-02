"""Provider stream-shape contract tests.

These pin the chunk shapes real providers emit, so the service layer cannot
silently drop or truncate a provider's output. They use recorded fixtures and
need no credentials, which is the point: the shape bug is reproducible in CI.

The Bedrock tool-call case is the regression this file exists for.
``ChatBedrockConverse`` streams tool arguments as fragmented
``tool_call_chunks``. A fragment on its own parses into a *truncated* argument
object, so a consumer that reads complete ``tool_calls`` per chunk emits a
mangled question and never revisits the merged result.
"""

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessageChunk

from preconsult.services.agent_service import stream_interview_questions

FIXTURES = Path(__file__).parent / "fixtures" / "llm"


def _chunks(fixture_name: str) -> list[AIMessageChunk]:
    payload = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    return [AIMessageChunk(**chunk) for chunk in payload["chunks"]]


class _StreamingStub:
    """Minimal stand-in for the interview chain: only ``astream`` is used."""

    def __init__(self, chunks: list[AIMessageChunk]) -> None:
        self._chunks = chunks

    async def astream(self, _input):
        for chunk in self._chunks:
            yield chunk


async def _collect(fixture_name: str):
    events = []
    async for event in stream_interview_questions(
        {}, "en", _StreamingStub(_chunks(fixture_name))
    ):
        events.append(event)
    return events


def _text(events) -> str:
    return "".join(event.value for event in events if event.kind == "text")


def _questions(events) -> list[list[str]]:
    return [event.value for event in events if event.kind == "questions"]


async def test_vertex_string_content_is_streamed():
    """Characterization: the shape the consumer was written against."""
    events = await _collect("vertex_text_stream.json")

    assert _text(events) == "1. When did the pain start?\n2. Does it spread anywhere?"
    assert _questions(events) == []


async def test_bedrock_content_blocks_are_streamed():
    """Bedrock sends text as content blocks; both providers must render the same."""
    events = await _collect("bedrock_converse_text_stream.json")

    assert _text(events) == "1. When did the pain start?\n2. Does it spread anywhere?"
    assert _questions(events) == []


@pytest.mark.xfail(
    strict=True,
    reason="partial tool_call_chunks are read per-chunk, so the question list is truncated (Wave 1)",
)
async def test_bedrock_partial_tool_chunks_emit_the_full_question_list():
    """The merged tool call is the contract, not any single fragment."""
    events = await _collect("bedrock_partial_tool_chunks.json")

    assert _questions(events) == [
        ["When did the pain start?", "Does it spread anywhere?"]
    ]


def test_non_text_content_blocks_are_ignored():
    """Reasoning/thinking blocks must never reach the renderer or the parser."""
    from preconsult.services.agent_service import _to_dict

    message = AIMessageChunk(
        content=[
            {"type": "thinking", "thinking": "internal reasoning"},
            {"type": "text", "text": "visible text"},
        ]
    )

    assert _to_dict(message)["content"] == "visible text"


async def test_bedrock_fake_emits_fragmented_tool_chunks():
    """Guard the double itself.

    A fake that emits one complete tool call cannot catch the fragment-assembly
    bug it exists to model, which is exactly how the defect shipped.
    """
    from tests.fakes import ToolCallingFakeLLM

    fake = ToolCallingFakeLLM(questions=["A?", "B?"], shape="bedrock")
    chunks = [chunk async for chunk in fake.astream({})]

    fragments = [
        chunk.tool_call_chunks[0]["args"] for chunk in chunks if chunk.tool_call_chunks
    ]

    assert len(fragments) == 2
    assert "".join(fragments) == '{"questions": ["A?", "B?"]}'
