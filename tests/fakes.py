"""Shared test doubles for the PreConsult test suite."""
from typing import Any

from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import Runnable


class ToolCallingFakeLLM(Runnable):
    """Minimal tool-capable fake chat model for stream tests.

    ``FakeListChatModel.bind_tools`` raises NotImplementedError, and the
    interview chain now always binds the ``report_questions`` tool. This fake is
    a ``Runnable`` (so ``prompt | fake`` composes) that emits the supplied text
    as content then an optional ``report_questions`` tool call — the shape the
    real Bedrock Converse stream produces.
    """

    def __init__(self, text: str = "", questions: list[str] | None = None):
        super().__init__()
        self._text = text
        self._questions = questions

    def bind_tools(self, tools, **kwargs: Any):  # noqa: ANN001 - test double
        return self

    def invoke(self, input, config=None, **kwargs):  # noqa: ANN001
        raise NotImplementedError("use astream in tests")

    async def ainvoke(self, input, config=None, **kwargs):  # noqa: ANN001
        raise NotImplementedError("use astream in tests")

    async def astream(self, input, config=None, **kwargs):  # noqa: ANN001
        if self._text:
            yield AIMessageChunk(content=self._text)
        if self._questions:
            yield AIMessageChunk(
                content="",
                tool_calls=[
                    {
                        "name": "report_questions",
                        "args": {"questions": self._questions},
                        "id": "call_1",
                    }
                ],
            )
