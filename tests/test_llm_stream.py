"""Unit tests for provider-agnostic stream assembly.

The end-to-end shape matrix lives in ``test_llm_stream_contract.py``; this file
covers the assembly rules in isolation.
"""

from langchain_core.messages import AIMessageChunk

from preconsult.core.llm_stream import (
    MAX_QUESTIONS,
    StreamAccumulator,
    clean_questions,
    flatten_content,
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
