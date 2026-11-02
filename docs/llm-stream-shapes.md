# LLM stream shapes

Three shapes reach `stream_interview_questions`, and the consumer must accept all
of them. The fixtures in `tests/fixtures/llm/` are the executable version of this
page; `tests/test_llm_stream_contract.py` feeds them through the real service
function.

## 1. Vertex / Gemini — string content

```python
AIMessageChunk(content="1. When did the pain start?")
```

`content` is a `str`. This was the only shape the service layer originally
handled, which is why the Gemini path looked correct.

## 2. Bedrock / Claude — content blocks

```python
AIMessageChunk(content=[{"type": "text", "text": "1. When did the pain start?"}])
```

`content` is a list of blocks. Non-text blocks (`thinking`, images, tool-use)
carry no `text` key and must be ignored, never rendered or parsed.

`agent_service._text_of()` flattens both shapes. It must stay the only place
that knows about block structure.

## 3. Bedrock / Claude — fragmented tool calls

This is the shape that broke.

```python
AIMessageChunk(content="", tool_call_chunks=[{
    "name": "report_questions",
    "args": '{"questions": ["When did the pain start?", "Does it spread',
    "id": "tooluse_abc",
    "index": 0,
}])
AIMessageChunk(content="", tool_call_chunks=[{
    "args": ' anywhere?"]}',
    "id": None, "name": None, "index": 0,
}])
```

Each fragment on its own parses into a **truncated** argument object: langchain
runs a partial-JSON repair, so fragment 1 yields
`{"questions": ["When did the pain start?", "Does it spread"]}`. A consumer that
reads `chunk.tool_calls` per chunk therefore emits a mangled final question and
never revisits the merged result.

**The contract is the merged call, not any fragment.** Merge before parsing:

```python
accumulated = chunk if accumulated is None else accumulated + chunk
# read accumulated.tool_calls only after the stream ends
```

`AIMessageChunk.__add__` concatenates string content, merges content-block
lists, joins `tool_call_chunks` by `index`, and sums `usage_metadata`. Verified
on `langchain-core 1.7.0`.

## Rules

1. Never assume `content` is a `str`.
2. Never read `tool_calls` from a single chunk of a streaming provider; read it
   from the accumulator after the stream ends.
3. Never emit a `questions` event from a partial list. If the final list is
   missing or invalid, fall back to `core.parsing.split_questions` over the
   accumulated text.
4. Record new provider shapes as fixtures before writing the adapter. A fake
   that emits the complete-call shape cannot catch this class of bug.

## Usage and stop metadata

Providers report token usage and the stop reason on their **last** chunk
(Vertex `usage_metadata` + `response_metadata.finish_reason`, Bedrock
`usage_metadata` + `response_metadata.stop_reason`). `StreamAccumulator.usage`
reduces that to neutral counts (`input_tokens`, `output_tokens`, and
`cache_read` when present) and `StreamAccumulator.finish_reason` to a short
enum. `deltas_from_chunks` attaches both to the **final** `LLMDelta`, combined
with the tool-call delta when there is one and emitted as a metadata-only delta
otherwise.

That keeps telemetry provider-neutral: `api/endpoints.py::_question_stream`
logs one `llm.stream` line per stream with counts/enums/durations only, and
`StreamEvent.source` (`"tool"` vs `"text"`) says how the final list was
obtained. Neither carries prompt or answer text.
