"""Shared test doubles for the PreConsult test suite."""

import json
from typing import Any, Literal

from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import Runnable

from preconsult.core.llm import deltas_from_chunks


class ToolCallingFakeLLM(Runnable):
    """Minimal tool-capable fake chat model for stream tests.

    Implements the ``LLMClient`` stream method (``astream(messages, tools)``)
    by producing provider-shaped chunks and normalizing them through the same
    ``deltas_from_chunks`` helper the real adapters use, so the test double
    exercises the assembly code instead of bypassing it.

    ``shape`` selects which real provider's wire format to imitate:

    * ``"vertex"`` (default) - string ``content`` and one complete ``tool_calls``
      entry. Preserves the behaviour existing tests were written against.
    * ``"bedrock"`` - ``content`` as a list of text blocks, and the tool call as
      two fragmented ``tool_call_chunks`` whose arguments are only valid JSON
      once concatenated, exactly as ``ChatBedrockConverse`` streams them.

    A fake that only ever emits the complete-call shape cannot catch the
    fragment-assembly bug, so tests that care about provider neutrality must run
    against ``shape="bedrock"`` too.
    """

    provider = "fake"

    def __init__(
        self,
        text: str = "",
        questions: list[str] | None = None,
        shape: Literal["vertex", "bedrock"] = "vertex",
    ):
        super().__init__()
        self._text = text
        self._questions = questions
        self._shape = shape
        self.model = f"fake-{shape}"

    def bind_tools(self, tools, **kwargs: Any):  # noqa: ANN001 - test double
        return self

    def invoke(self, input, config=None, **kwargs):  # noqa: ANN001
        raise NotImplementedError("use astream in tests")

    async def ainvoke(self, input, config=None, **kwargs):  # noqa: ANN001
        raise NotImplementedError("use astream in tests")

    async def astream(self, messages=None, tools=None, **kwargs):  # noqa: ANN001
        async for delta in deltas_from_chunks(self.chunks()):
            yield delta

    def chunks(self) -> list[AIMessageChunk]:
        """The raw provider-shaped chunks this fake would stream."""
        chunks: list[AIMessageChunk] = []

        if self._text:
            if self._shape == "bedrock":
                chunks.append(
                    AIMessageChunk(content=[{"type": "text", "text": self._text}])
                )
            else:
                chunks.append(AIMessageChunk(content=self._text))

        if self._questions:
            if self._shape == "bedrock":
                chunks.extend(self._bedrock_tool_chunks())
            else:
                chunks.append(
                    AIMessageChunk(
                        content="",
                        tool_calls=[
                            {
                                "name": "report_questions",
                                "args": {"questions": self._questions},
                                "id": "call_1",
                            }
                        ],
                    )
                )

        return chunks

    def _bedrock_tool_chunks(self) -> list[AIMessageChunk]:
        """Split the tool arguments mid-value, as real Converse deltas do."""
        args = json.dumps({"questions": self._questions})
        cut = len(args) // 2
        return [
            AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {
                        "name": "report_questions",
                        "args": args[:cut],
                        "id": "call_1",
                        "index": 0,
                    }
                ],
            ),
            AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {"args": args[cut:], "id": None, "name": None, "index": 0}
                ],
            ),
        ]


def session_payload(**overrides: object) -> dict:
    """A valid POST /api/session/init body.

    One definition of the session schema for the whole suite: a test that cares
    about a few fields overrides those keys instead of restating the other
    eleven. Every field is optional server-side, so the minimal shape here is a
    valid request. Returns a fresh dict, so callers may mutate it.
    """
    payload: dict = {
        "age_bracket": "26-35",
        "sex": "Female",
        "lang": "en",
        "specialist": "Cardiology",
        "chief_complaint": "Chest pain",
        "duration": "2 days",
    }
    payload.update(overrides)
    return payload
