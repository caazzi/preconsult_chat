"""Unit tests for provider-agnostic stream assembly.

The end-to-end shape matrix lives in ``test_llm_stream_contract.py``; this file
covers the assembly rules in isolation.
"""

from langchain_core.messages import AIMessageChunk

import pytest

from preconsult.core.llm import deltas_from_chunks
from preconsult.core.llm_stream import (
    MAX_QUESTIONS,
    StreamAccumulator,
    clean_questions,
    finish_reason_from,
    flatten_content,
    normalize_usage,
    questions_from_text,
    questions_from_tool_calls,
)


def test_flatten_content_accepts_strings_blocks_and_ignores_non_text():
    assert flatten_content("hello") == "hello"
    assert flatten_content(None) == ""
    assert flatten_content(["a", "b"]) == "ab"
    assert (
        flatten_content(
            [
                {"type": "text", "text": "a"},
                {"type": "image_url", "image_url": {"url": "ignored"}},
                {"type": "text", "text": "b"},
            ]
        )
        == "ab"
    )
    assert flatten_content([{"type": "thinking", "thinking": "secret"}]) == ""


def test_accumulator_returns_each_delta_and_the_full_text():
    accumulator = StreamAccumulator()

    assert accumulator.feed(AIMessageChunk(content="Hel")) == "Hel"
    assert (
        accumulator.feed(AIMessageChunk(content=[{"type": "text", "text": "lo"}]))
        == "lo"
    )
    assert accumulator.text == "Hello"


def test_accumulator_merges_fragmented_tool_calls():
    accumulator = StreamAccumulator()
    accumulator.feed(
        AIMessageChunk(
            content="",
            tool_call_chunks=[
                {
                    "name": "report_questions",
                    "args": '{"questions": ["A?',
                    "id": "tooluse_1",
                    "index": 0,
                }
            ],
        )
    )
    accumulator.feed(
        AIMessageChunk(
            content="",
            tool_call_chunks=[
                {"args": '", "B?"]}', "id": None, "name": None, "index": 0}
            ],
        )
    )

    assert questions_from_tool_calls(accumulator.tool_calls) == ["A?", "B?"]


def test_tool_calls_complete_rejects_a_truncated_fragment():
    accumulator = StreamAccumulator()
    accumulator.feed(
        AIMessageChunk(
            content="",
            tool_call_chunks=[
                {
                    "name": "report_questions",
                    "args": '{"questions": ["A?',
                    "id": "tooluse_1",
                    "index": 0,
                }
            ],
        )
    )

    assert accumulator.tool_calls_complete is False


def test_tool_calls_complete_accepts_a_merged_call():
    accumulator = StreamAccumulator()
    accumulator.feed(
        AIMessageChunk(
            content="",
            tool_call_chunks=[
                {
                    "name": "report_questions",
                    "args": '{"questions": ["A?"',
                    "id": "tooluse_1",
                    "index": 0,
                }
            ],
        )
    )
    accumulator.feed(
        AIMessageChunk(
            content="",
            tool_call_chunks=[{"args": "]}", "id": None, "name": None, "index": 0}],
        )
    )

    assert accumulator.tool_calls_complete is True


def test_accumulator_accepts_dict_chunks():
    """The service keeps working with plain dicts, which tests rely on."""
    accumulator = StreamAccumulator()
    accumulator.feed(
        {
            "content": "x",
            "tool_calls": [
                {"name": "report_questions", "args": {"questions": ["A?", "B?"]}}
            ],
        }
    )

    assert accumulator.text == "x"
    assert questions_from_tool_calls(accumulator.tool_calls) == ["A?", "B?"]


def test_clean_questions_strips_dedupes_and_caps():
    assert clean_questions(["  A?\n", "a?", "", None, "B?"]) == ["A?", "B?"]
    assert clean_questions([]) is None
    assert clean_questions("not a list") is None
    assert clean_questions(["x" * 401]) is None
    assert len(clean_questions([f"Q{i}?" for i in range(9)])) == MAX_QUESTIONS


def test_questions_from_tool_calls_handles_raw_json_string_args():
    assert questions_from_tool_calls(
        [{"name": "report_questions", "args": '{"questions": ["A?", "B?"]}'}]
    ) == ["A?", "B?"]
    assert (
        questions_from_tool_calls([{"name": "report_questions", "args": "{not json"}])
        is None
    )


def test_questions_from_tool_calls_ignores_other_tools_and_junk():
    assert (
        questions_from_tool_calls([{"name": "other", "args": {"questions": ["A?"]}}])
        is None
    )
    assert questions_from_tool_calls([{"name": "report_questions", "args": {}}]) is None
    assert questions_from_tool_calls(["not-a-call"]) is None
    assert questions_from_tool_calls(None) is None


def test_questions_from_text_requires_a_list():
    assert questions_from_text("1. A?\n2. B?") == ["A?", "B?"]
    assert questions_from_text("Only one line?") is None
    assert questions_from_text("") is None


def test_questions_from_text_never_relabels_emergency_prose():
    assert questions_from_text("[EMERGENCY ALERT] Call 911 immediately.") is None
    assert questions_from_text("1. Call 911?\n2. This is an emergency?") is None


def test_accumulator_reads_usage_and_finish_reason_from_object_chunks():
    accumulator = StreamAccumulator()
    accumulator.feed(
        AIMessageChunk(
            content="hi",
            usage_metadata={
                "input_tokens": 12,
                "output_tokens": 3,
                "total_tokens": 15,
                "input_token_details": {"cache_read": 7},
            },
        )
    )
    accumulator.feed(
        AIMessageChunk(content="", response_metadata={"finish_reason": "stop"})
    )

    assert accumulator.usage == {
        "input_tokens": 12,
        "output_tokens": 3,
        "cache_read": 7,
    }
    assert accumulator.finish_reason == "stop"


def test_accumulator_reads_usage_and_finish_reason_from_dict_chunks():
    accumulator = StreamAccumulator()
    accumulator.feed(
        {
            "content": "hi",
            "usage_metadata": {"input_tokens": 4, "output_tokens": 1},
            "response_metadata": {"stop_reason": "end_turn"},
        }
    )

    assert accumulator.usage == {"input_tokens": 4, "output_tokens": 1}
    assert accumulator.finish_reason == "end_turn"


def test_accumulator_without_metadata_reports_none():
    accumulator = StreamAccumulator()
    accumulator.feed(AIMessageChunk(content="plain"))

    assert accumulator.usage is None
    assert accumulator.finish_reason is None


def test_normalize_usage_ignores_non_counts_and_non_dicts():
    assert normalize_usage(None) is None
    assert normalize_usage({"input_tokens": True, "output_tokens": "9"}) is None
    assert normalize_usage(
        {
            "input_tokens": 5,
            "output_tokens": 2,
            "input_token_details": {"cache_read": "many"},
        }
    ) == {"input_tokens": 5, "output_tokens": 2}
    assert finish_reason_from({"finish_reason": ""}) is None
    assert finish_reason_from({"stop_reason": "end_turn"}) == "end_turn"
    assert finish_reason_from(None) is None


@pytest.mark.asyncio
async def test_deltas_from_chunks_surfaces_metadata_without_a_tool_call():
    chunks = [
        AIMessageChunk(
            content="1. A?\n2. B?",
            usage_metadata={
                "input_tokens": 9,
                "output_tokens": 4,
                "total_tokens": 13,
                "input_token_details": {"cache_read": 2},
            },
            response_metadata={"finish_reason": "stop"},
        )
    ]

    deltas = [delta async for delta in deltas_from_chunks(chunks)]

    assert [delta.text for delta in deltas if delta.text] == ["1. A?\n2. B?"]
    assert deltas[-1].tool_calls == ()
    assert deltas[-1].usage == {
        "input_tokens": 9,
        "output_tokens": 4,
        "cache_read": 2,
    }
    assert deltas[-1].finish_reason == "stop"
