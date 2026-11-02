"""Provider-agnostic assembly of a streaming chat response.

Providers disagree about chunk shape:

* Vertex/Gemini sends ``content`` as a ``str``.
* Bedrock/Claude sends ``content`` as a list of blocks.
* Bedrock fragments tool arguments across ``tool_call_chunks``, and each
  fragment on its own parses into a valid-but-*truncated* argument object.

This module is the only place that knows those differences. The service layer
feeds chunks into :class:`StreamAccumulator` and reads the merged result once
the stream ends, so no provider's per-chunk semantics leak upward.
"""

from __future__ import annotations

import json
from typing import Any

from preconsult.core.parsing import is_emergency_trigger, split_questions

MAX_QUESTIONS = 5
MAX_QUESTION_CHARS = 400


def flatten_content(content: Any) -> str:
    """Flatten message content to text.

    ``content`` may be a string, a list of blocks, or ``None``. Only blocks with
    a string ``text`` field contribute; images, tool-use and reasoning blocks
    are ignored because nothing downstream renders or parses them.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _merge(left: Any, right: Any) -> Any:
    """Merge two chunks, tolerating messages that do not support ``+``."""
    try:
        return left + right
    except TypeError:
        return right


def _raw_args_by_index(tool_call_chunks: Any) -> dict[int, str]:
    """Group fragmented tool arguments by tool-call index and concatenate them."""
    grouped: dict[int, list[str]] = {}
    for chunk in tool_call_chunks or []:
        if not isinstance(chunk, dict):
            continue
        index = chunk.get("index")
        key = index if isinstance(index, int) else 0
        grouped.setdefault(key, []).append(chunk.get("args") or "")
    return {index: "".join(parts) for index, parts in grouped.items()}


def _metadata_of(chunk: Any, key: str) -> Any:
    """Read ``key`` from an object chunk or a plain dict chunk."""
    if isinstance(chunk, dict):
        return chunk.get(key)
    return getattr(chunk, key, None)


def normalize_usage(metadata: Any) -> dict | None:
    """Reduce provider ``usage_metadata`` to neutral token counts.

    Providers name the cache hit differently (``input_token_details.cache_read``
    on both current adapters); the returned dict keeps that name and adds
    nothing derived from user content. Returns ``None`` when no counts exist, so
    a stream without usage telemetry is distinguishable from a zero-token one.
    """
    if not isinstance(metadata, dict):
        return None

    usage: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens"):
        value = metadata.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            usage[key] = value

    details = metadata.get("input_token_details")
    if isinstance(details, dict):
        cached = details.get("cache_read")
        if isinstance(cached, int) and not isinstance(cached, bool):
            usage["cache_read"] = cached

    return usage or None


def finish_reason_from(metadata: Any) -> str | None:
    """Best-effort stop reason from provider ``response_metadata``.

    Vertex/Gemini reports ``finish_reason``; Bedrock/Claude reports
    ``stop_reason``. Both are short enums (``stop``, ``end_turn``, ``length``),
    never user content.
    """
    if not isinstance(metadata, dict):
        return None
    for key in ("finish_reason", "stop_reason"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None


class StreamAccumulator:
    """Accumulates a provider stream into its final text and tool calls.

    ``feed`` returns the text delta contributed by that chunk, so the caller can
    render progressively without re-reading the whole buffer. Tool calls are
    only meaningful after the stream ends: a fragment is not a call.
    """

    def __init__(self) -> None:
        self._text_parts: list[str] = []
        self._merged: Any = None
        self._dict_tool_calls: list = []
        # Usage/stop metadata for dict-shaped chunks, where there is no merged
        # message to read after the stream (object chunks are read from
        # ``self._merged``; AIMessageChunk sums usage_metadata on ``+``).
        self._dict_usage: dict | None = None
        self._dict_finish_reason: str | None = None

    def feed(self, chunk: Any) -> str:
        """Add one chunk and return the text it contributed (possibly empty)."""
        if isinstance(chunk, dict):
            content = chunk.get("content", "")
            tool_calls = chunk.get("tool_calls")
            if tool_calls:
                self._dict_tool_calls = tool_calls
        else:
            content = getattr(chunk, "content", "")

        text = flatten_content(content)
        if text:
            self._text_parts.append(text)

        if not isinstance(chunk, dict):
            self._merged = (
                chunk if self._merged is None else _merge(self._merged, chunk)
            )
        else:
            # Dict chunks are never merged, so keep the last metadata seen.
            usage = normalize_usage(chunk.get("usage_metadata"))
            if usage is not None:
                self._dict_usage = usage
            reason = finish_reason_from(chunk.get("response_metadata"))
            if reason is not None:
                self._dict_finish_reason = reason

        return text

    @property
    def usage(self) -> dict | None:
        """Provider-reported token counts, or ``None`` when the stream had none."""
        merged_usage = normalize_usage(_metadata_of(self._merged, "usage_metadata"))
        return merged_usage if merged_usage is not None else self._dict_usage

    @property
    def finish_reason(self) -> str | None:
        """Provider-reported stop reason, best effort."""
        merged_reason = finish_reason_from(
            _metadata_of(self._merged, "response_metadata")
        )
        return merged_reason if merged_reason is not None else self._dict_finish_reason

    @property
    def text(self) -> str:
        return "".join(self._text_parts)

    @property
    def tool_calls(self) -> list:
        """The merged tool calls. Only valid after the stream has ended."""
        if self._merged is not None:
            return list(getattr(self._merged, "tool_calls", None) or [])
        return list(self._dict_tool_calls)

    @property
    def tool_calls_complete(self) -> bool:
        """Whether the merged arguments are valid JSON, not a truncated prefix.

        LangChain repairs partial JSON, so an unfinished tool call still yields
        a *parsed* ``tool_calls`` entry -- with the last question cut short. The
        repaired object looks valid, so completeness has to be checked against
        the raw concatenated fragments instead.
        """
        if self._merged is None:
            return True

        raw_arguments = _raw_args_by_index(
            getattr(self._merged, "tool_call_chunks", None) or []
        )
        for raw in raw_arguments.values():
            if not raw:
                continue
            try:
                json.loads(raw)
            except json.JSONDecodeError:
                return False
        return True


def clean_questions(items: Any) -> list[str] | None:
    """Normalize a question list: strip, collapse whitespace, dedupe, cap at 5.

    There is deliberately no minimum-count gate. The prompt and the tool schema
    ask for 3-5 items, but discarding a real 2-item answer is worse than
    returning it: the client would render the same two questions from the text
    fallback anyway, and a hard gate would turn a short answer into silence.
    """
    if not isinstance(items, list):
        return None

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        question = " ".join(item.split())
        if not question or len(question) > MAX_QUESTION_CHARS:
            continue
        key = question.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(question)
        if len(cleaned) == MAX_QUESTIONS:
            break

    return cleaned or None


def questions_from_tool_calls(
    tool_calls: Any, tool_name: str = "report_questions"
) -> list[str] | None:
    """Extract the first valid ``tool_name`` call's questions.

    ``args`` is normally a dict after LangChain parses the merged call, but a
    provider may hand back the raw JSON string, which must not raise.
    """
    for tool_call in tool_calls or []:
        if not isinstance(tool_call, dict):
            continue
        if tool_call.get("name") != tool_name:
            continue

        args = tool_call.get("args")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                continue
        if not isinstance(args, dict):
            continue

        questions = clean_questions(args.get("questions"))
        if questions:
            return questions

    return None


def questions_from_text(text: str) -> list[str] | None:
    """Salvage a question list from prose when no tool call arrived.

    Two guards stop the fallback from inventing structure that is not there:
    emergency prose is never re-labelled as questions (the client renders it in
    the emergency dialog, not as cards), and a single line is not a list.
    """
    if not text.strip() or is_emergency_trigger(text):
        return None

    parts = split_questions(text)
    if len(parts) < 2:
        return None

    return clean_questions(parts)
