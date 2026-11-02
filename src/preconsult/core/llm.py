"""Model client seam.

One provider is active per deployment, selected by ``LLM_PROVIDER``. Each
provider is an adapter that turns its own streaming chunks into a neutral
``LLMDelta``; nothing above this module knows a provider's wire format.

Adding a provider is one adapter class plus one registry entry. Vendor SDKs are
imported inside the adapter constructor, so the default image only pays for the
provider it actually uses.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

from preconsult.core.config import (
    BEDROCK_REGION,
    LLM_IDLE_TIMEOUT_S,
    LLM_MAX_RETRIES,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_REGION,
    LLM_TEMPERATURE,
    LLM_TTFT_TIMEOUT_S,
    PROJECT_ID,
    VERTEX_REGION,
)
from preconsult.core.errors import LLMUpstreamError
from preconsult.core.llm_stream import StreamAccumulator


@dataclass(frozen=True)
class LLMDelta:
    """One normalized unit of a provider stream.

    Either text (render it) or a set of *complete* tool calls (use it). A
    provider must never expose a partial tool call as an ``LLMDelta``.

    ``usage`` and ``finish_reason`` are provider-reported metadata, carried on
    the final delta of every stream (possibly combined with the tool-call
    delta). They contain counts/enums only, never prompt or answer text.
    """

    text: str = ""
    tool_calls: tuple[dict, ...] = ()
    usage: dict | None = None
    finish_reason: str | None = None


class LLMClient(Protocol):
    """What the service layer needs from a provider, and nothing more."""

    provider: str
    model: str

    def astream(
        self, messages: list, tools: list | None = None
    ) -> AsyncIterator[LLMDelta]: ...


@dataclass
class StreamMeta:
    """Provider-reported metadata observed from one stream."""

    usage: dict | None = None
    finish_reason: str | None = None


class DeltaStream(Protocol):
    """Anything that streams neutral deltas for one prompt input."""

    def astream(self, input_dict: dict) -> AsyncIterator[LLMDelta]: ...


class _ObservedStream:
    """Pass-through stream that records usage/finish_reason into ``StreamMeta``.

    Deltas are yielded unchanged; nothing is buffered or reordered, so a
    consumer's rendering and timing are unaffected.
    """

    def __init__(self, chain: DeltaStream, meta: StreamMeta) -> None:
        self._chain = chain
        self._meta = meta

    async def astream(self, input_dict: dict) -> AsyncIterator[LLMDelta]:
        async for delta in self._chain.astream(input_dict):
            usage = getattr(delta, "usage", None)
            if isinstance(usage, dict) and usage:
                self._meta.usage = usage
            reason = getattr(delta, "finish_reason", None)
            if isinstance(reason, str) and reason:
                self._meta.finish_reason = reason
            yield delta


def observe_stream(chain: DeltaStream, meta: StreamMeta) -> DeltaStream:
    """Wrap ``chain`` so its metadata is collected in one place.

    The service layer supplies ``input_dict`` when it calls ``astream``, so the
    wrapper stays chain-shaped instead of binding a prompt at wrap time. This is
    the single observer used by both the API telemetry and the benchmark.
    """
    return _ObservedStream(chain, meta)


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    region: str
    temperature: float
    max_tokens: int
    ttft_timeout_s: float
    idle_timeout_s: float
    max_retries: int


async def _aiter(chunks):
    """Iterate chunks from either an async stream or a plain list."""
    if hasattr(chunks, "__aiter__"):
        async for chunk in chunks:
            yield chunk
        return
    for chunk in chunks:
        yield chunk


async def deltas_from_chunks(chunks) -> AsyncIterator[LLMDelta]:
    """Normalize a provider chunk stream, emitting only complete tool calls.

    Shared by every adapter and by the contract tests, so the fixtures exercise
    the same assembly code the deployed provider uses.

    The last delta also carries the stream's ``usage``/``finish_reason`` (when
    the provider reported them), even for a stream with no tool call, so
    telemetry never has to know a provider's chunk shape.
    """
    accumulator = StreamAccumulator()
    async for chunk in _aiter(chunks):
        text = accumulator.feed(chunk)
        if text:
            yield LLMDelta(text=text)

    usage = accumulator.usage
    finish_reason = accumulator.finish_reason

    if accumulator.tool_calls_complete and accumulator.tool_calls:
        yield LLMDelta(
            tool_calls=tuple(accumulator.tool_calls),
            usage=usage,
            finish_reason=finish_reason,
        )
    elif usage is not None or finish_reason is not None:
        yield LLMDelta(usage=usage, finish_reason=finish_reason)


async def _with_timeouts(
    source,
    *,
    ttft_timeout: float,
    idle_timeout: float,
    provider: str,
) -> AsyncIterator[LLMDelta]:
    """Apply a first-token budget and an inter-token idle budget.

    Not a total duration: a total timeout would truncate a legitimately long
    answer. Exceeding either budget surfaces as a retriable ``timeout``.
    """
    iterator = source.__aiter__()
    first = True
    try:
        while True:
            timeout = ttft_timeout if first else idle_timeout
            try:
                delta = await asyncio.wait_for(anext(iterator), timeout=timeout)
            except StopAsyncIteration:
                return
            except (asyncio.TimeoutError, TimeoutError) as exc:
                raise LLMUpstreamError("timeout", provider=provider) from exc
            first = False
            yield delta
    finally:
        aclose = getattr(iterator, "aclose", None)
        if aclose is not None:
            await aclose()


def _classify_bedrock(exc: Exception) -> str:
    try:
        from botocore.exceptions import (
            ClientError,
            NoCredentialsError,
            ReadTimeoutError,
        )
    except ImportError:  # pragma: no cover - the bedrock extra is installed in CI
        return "upstream"

    if isinstance(exc, NoCredentialsError):
        return "auth"
    if isinstance(exc, ReadTimeoutError):
        return "timeout"
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        lowered = code.lower()
        if "throttl" in lowered or code in (
            "TooManyRequestsException",
            "ServiceQuotaExceededException",
        ):
            return "throttled"
        if any(
            token in lowered
            for token in ("accessdenied", "unrecognizedclient", "expiredtoken")
        ):
            return "auth"
        if any(token in lowered for token in ("validation", "invalidparameter")):
            return "invalid_request"
    return "upstream"


def _classify_vertex(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    status = str(getattr(exc, "status", "")).upper()

    if code == 429 or status in {"RESOURCE_EXHAUSTED", "TOO_MANY_REQUESTS"}:
        return "throttled"
    if code in (401, 403) or status in {"UNAUTHENTICATED", "PERMISSION_DENIED"}:
        return "auth"
    if code == 400 or status == "INVALID_ARGUMENT":
        return "invalid_request"
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "timeout"

    message = str(exc).lower()
    if "429" in message or "resource exhausted" in message:
        return "throttled"
    return "upstream"


class _LangChainClient:
    """Shared stream plumbing; subclasses supply the chat model and classifier."""

    provider = ""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.model = config.model
        try:
            self._chat = self._build()
        except RuntimeError:
            # The actionable "install the bedrock extra" message must reach
            # the operator unchanged.
            raise
        except Exception as exc:
            # A credential/model failure at construction is an upstream error
            # (502/503), not a 500 from the generic handler.
            raise LLMUpstreamError(self._kind_of(exc), provider=self.provider) from exc

    def _build(self):  # pragma: no cover - implemented by each adapter
        raise NotImplementedError

    def _kind_of(self, exc: Exception) -> str:
        return "upstream"

    async def astream(
        self, messages: list, tools: list | None = None
    ) -> AsyncIterator[LLMDelta]:
        chat = self._chat.bind_tools(tools) if tools else self._chat
        attempts = max(self.config.max_retries, 0) + 1

        for attempt in range(attempts):
            emitted = False
            try:
                stream = _with_timeouts(
                    deltas_from_chunks(chat.astream(messages)),
                    ttft_timeout=self.config.ttft_timeout_s,
                    idle_timeout=self.config.idle_timeout_s,
                    provider=self.provider,
                )
                async for delta in stream:
                    emitted = True
                    yield delta
                return
            except LLMUpstreamError as exc:
                # Never retry after output started: the client already rendered
                # part of the answer and a replay would duplicate it.
                if emitted or not exc.retryable or attempt == attempts - 1:
                    raise
            except Exception as exc:
                error = LLMUpstreamError(self._kind_of(exc), provider=self.provider)
                if emitted or not error.retryable or attempt == attempts - 1:
                    raise error from exc

            await asyncio.sleep(min(0.5 * (2**attempt), 4.0))


class VertexClient(_LangChainClient):
    provider = "vertex"

    def _build(self):
        # google-genai based provider: no google-cloud-aiplatform/grpcio.
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=self.config.model,
            vertexai=True,
            project=PROJECT_ID,
            location=self.config.region,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
            streaming=True,
            # Retries and timeouts are owned by this adapter; the SDK's own
            # retries would double the delay and hide the TTFT budget.
            max_retries=0,
            timeout=self.config.ttft_timeout_s,
        )

    def _kind_of(self, exc: Exception) -> str:
        return _classify_vertex(exc)


class BedrockClient(_LangChainClient):
    provider = "bedrock"

    def _build(self):
        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError as exc:
            # Bedrock is an opt-in extra so the default image does not carry
            # boto3/botocore for a provider it has no credentials for. Surface
            # a config error, not an opaque 500 on the first question.
            raise RuntimeError(
                "LLM_PROVIDER=bedrock requires the 'bedrock' extra, which the "
                "default image does not install. Rebuild with "
                "`uv sync --locked --extra bedrock` (see AGENTS.md)."
            ) from exc

        return ChatBedrockConverse(
            model=self.config.model,
            region_name=self.config.region,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

    def _kind_of(self, exc: Exception) -> str:
        return _classify_bedrock(exc)


PROVIDERS: dict[str, type[_LangChainClient]] = {
    "vertex": VertexClient,
    "bedrock": BedrockClient,
}


def build_client(config: LLMConfig) -> LLMClient:
    """Instantiate the adapter for ``config.provider``.

    Unknown names raise here rather than silently falling back to Vertex.
    """
    try:
        adapter = PROVIDERS[config.provider]
    except KeyError:
        raise ValueError(
            f"LLM_PROVIDER={config.provider!r} is not supported; "
            f"choose one of {sorted(PROVIDERS)}."
        ) from None
    return adapter(config)


def config_from_env() -> LLMConfig:
    provider = LLM_PROVIDER
    region = LLM_REGION or (BEDROCK_REGION if provider == "bedrock" else VERTEX_REGION)
    return LLMConfig(
        provider=provider,
        model=LLM_MODEL,
        region=region,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        ttft_timeout_s=LLM_TTFT_TIMEOUT_S,
        idle_timeout_s=LLM_IDLE_TIMEOUT_S,
        max_retries=LLM_MAX_RETRIES,
    )


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    """Return the process-wide provider adapter for the configured provider."""
    global _llm
    if _llm is None:
        logging.info("Initializing %s LLM for the first time...", LLM_PROVIDER)
        _llm = build_client(config_from_env())
        logging.info("%s LLM initialized successfully.", LLM_PROVIDER)
    return _llm
