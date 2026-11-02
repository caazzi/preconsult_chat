#!/usr/bin/env python3
"""Offline-first benchmark/regression harness for interview-question LLMs.

The harness drives the *real* service seam --
``preconsult.services.agent_service.stream_interview_questions`` -- with no
HTTP server, no Redis and no session. That means it measures the code the app
actually runs (prompt, provider adapter, stream assembly, question parsing)
instead of a second prompt path that could drift.

Modes
-----
``--provider fake``
    Fully offline and deterministic. A local ``LLMClient`` yields canned
    questions derived from each synthetic fixture's expected dimensions. This is
    the only mode allowed in CI. It validates the harness and rubric, not the
    quality of a real model.

``--provider vertex`` / ``--provider bedrock``
    Live calls. Human-invoked only; never part of the test suite or CI. The
    script prints a live-mode banner. Provider credentials come from the normal
    environment (Vertex ADC / AWS credential chain).

Examples
--------
    uv run python scripts/bench_llm.py --provider fake --repeat 1 --out /tmp/bench
    uv run python scripts/bench_llm.py --providers vertex,bedrock --repeat 3

Outputs
-------
``run.json``    machine-readable per-call metrics + aggregates.
``report.md``   human-readable aggregate tables.

Default output directory is ``outputs/llm-bench/<UTC timestamp>/`` (gitignored).
Pass ``--out`` to write directly to a chosen directory.

PHI / privacy
-------------
Fixtures are synthetic and committed. Live runs write only aggregate metrics and
scores: never prompts, never raw model answers. The zero-PHI rule applies to
benchmark artifacts too.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.bench_pricing import (  # noqa: E402 - sys.path bootstrap above
    FAKE_MODELS,
    PRICING_AS_OF,
    UnknownModelError,
    estimate_cost_usd,
    format_usd,
    get_price,
)
from scripts.bench_scoring import (  # noqa: E402 - sys.path bootstrap above
    KNOWN_DIMENSIONS,
    QualityScore,
    aggregate_quality,
    score_questions,
)

DEFAULT_FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "bench" / "complaints.json"
DEFAULT_MAX_CALLS = 600
DEFAULT_MAX_COST_USD = 5.0
DEFAULT_MAX_CONCURRENCY = 2
DEFAULT_REPEAT = 3
DEFAULT_LANGS = "en,pt"

# Token counts are estimated at ~4 characters/token because the LLMDelta seam
# deliberately drops provider usage metadata (nothing above the seam needs it).
# The number is a budgeting/regression signal, not a billed token count.
CHARS_PER_TOKEN = 4
# Generous upper bound for the formatted system + human prompt when reserving
# budget. The actual benchmark prompt is far smaller (the system prompt is a few
# thousand characters); this keeps the hard cap conservative without a
# tokenizer dependency.
PROMPT_TOKEN_UPPER_BOUND = 4096

DEFAULT_MODELS = {
    "vertex": "gemini-2.5-flash",
    "bedrock": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "fake": "fake-deterministic",
}

FAKE_QUESTION_BANK: dict[str, dict[str, str]] = {
    "en": {
        "onset": "When did the discomfort first start?",
        "provocation": "What makes the discomfort worse?",
        "palliation": "What makes the discomfort better?",
        "quality": "How would you describe the feeling?",
        "region": "Where do you feel it most?",
        "radiation": "Does the feeling spread anywhere else?",
        "severity": "On a scale from 1 to 10, how severe is it?",
        "timing": "How often does it happen?",
        "associated": "Have you noticed any other symptoms along with it?",
        "allergies": "Do you have any allergies?",
        "medications": "Are you currently taking any medications?",
        "past_history": "Have you had this problem before?",
        "last_intake": "When did you last eat or drink?",
        "events": "What happened right before it started?",
    },
    "pt": {
        "onset": "Quando o desconforto começou?",
        "provocation": "O que faz o desconforto piorar?",
        "palliation": "O que faz o desconforto melhorar?",
        "quality": "Como você descreve a sensação?",
        "region": "Onde você sente isso?",
        "radiation": "O desconforto se espalha para outro lugar?",
        "severity": "Numa escala de 1 a 10, quão forte é?",
        "timing": "Com que frequência isso acontece?",
        "associated": "Você notou outros sintomas junto com isso?",
        "allergies": "Você tem alguma alergia?",
        "medications": "Você está tomando algum remédio?",
        "past_history": "Você já teve esse problema no passado?",
        "last_intake": "Quando foi a última vez que você comeu ou bebeu?",
        "events": "O que aconteceu antes de começar?",
    },
}


class BenchConfigError(ValueError):
    """A bad flag, fixture or model selection; exit code 3."""


class RunAborted(Exception):
    """A hard budget or call cap stopped the run; exit code 2."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class Fixture:
    id: str
    lang: str
    session: dict[str, Any]
    expected_dimensions: tuple[str, ...]


@dataclass(frozen=True)
class CallSpec:
    provider: str
    model: str
    fixture: Fixture
    repeat: int


@dataclass(frozen=True)
class ClientRow:
    provider: str
    model: str
    client: Any | None
    setup_error: str | None


@dataclass
class CallResult:
    provider: str
    model: str
    lang: str
    fixture_id: str
    repeat: int
    ok: bool
    error_kind: str | None
    ttft_ms: float | None
    duration_ms: float
    prompt_tokens_est: int
    output_tokens_est: int
    cost_usd_est: float
    question_count: int
    questions: tuple[str, ...] | None
    score: QualityScore | None

    def to_dict(self, *, include_questions: bool, include_banned_terms: bool) -> dict:
        payload: dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
            "lang": self.lang,
            "fixture_id": self.fixture_id,
            "repeat": self.repeat,
            "ok": self.ok,
            "error_kind": self.error_kind,
            "ttft_ms": self.ttft_ms,
            "duration_ms": self.duration_ms,
            "prompt_tokens_est": self.prompt_tokens_est,
            "output_tokens_est": self.output_tokens_est,
            "cost_usd_est": self.cost_usd_est,
            "question_count": self.question_count,
        }
        if include_questions and self.questions is not None:
            payload["questions"] = list(self.questions)
        if self.score is not None:
            payload["score"] = _score_to_dict(
                self.score, include_banned_terms=include_banned_terms
            )
        return payload


@dataclass
class AggregateRow:
    provider: str
    model: str
    lang: str
    calls: int = 0
    ok: int = 0
    throttled: int = 0
    failed: int = 0
    ttft_p50_ms: float | None = None
    ttft_p95_ms: float | None = None
    duration_p50_ms: float | None = None
    duration_p95_ms: float | None = None
    prompt_tokens_est: int = 0
    output_tokens_est: int = 0
    cost_usd_est: float = 0.0
    quality: dict[str, float] = field(default_factory=dict)

    @property
    def error_rate(self) -> float:
        return self.failed / self.calls if self.calls else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "lang": self.lang,
            "calls": self.calls,
            "ok": self.ok,
            "throttled": self.throttled,
            "failed": self.failed,
            "error_rate": self.error_rate,
            "ttft_p50_ms": self.ttft_p50_ms,
            "ttft_p95_ms": self.ttft_p95_ms,
            "duration_p50_ms": self.duration_p50_ms,
            "duration_p95_ms": self.duration_p95_ms,
            "prompt_tokens_est": self.prompt_tokens_est,
            "output_tokens_est": self.output_tokens_est,
            "cost_usd_est": self.cost_usd_est,
            "quality": self.quality,
        }


class BudgetTracker:
    """Reserve worst-case cost per call, settle with the estimate after it runs.

    A call is only started when ``actual_spent + reserved + worst_case`` fits
    the cap, so the *estimated* spend can never cross the cap. Token counts are
    estimates, which is why this is a budgeting guard rather than an invoice.
    """

    def __init__(self, max_calls: int, max_cost_usd: float) -> None:
        self.max_calls = max_calls
        self.max_cost_usd = max_cost_usd
        self.calls_started = 0
        self.reserved_cost = 0.0
        self.actual_cost = 0.0
        self.abort_reason: str | None = None
        self.abort_detail: str | None = None
        self._lock = asyncio.Lock()

    async def reserve(self, worst_case_cost: float) -> None:
        async with self._lock:
            if self.abort_reason is not None:
                raise RunAborted(self.abort_reason, self.abort_detail or "")
            if self.calls_started >= self.max_calls:
                self.abort_reason = "max_calls"
                self.abort_detail = (
                    f"call cap reached: {self.calls_started} of "
                    f"{self.max_calls} calls started"
                )
                raise RunAborted(self.abort_reason, self.abort_detail)
            projected = self.actual_cost + self.reserved_cost + worst_case_cost
            if projected > self.max_cost_usd + 1e-12:
                self.abort_reason = "max_cost_usd"
                self.abort_detail = (
                    "cost cap reached: "
                    f"${self.actual_cost + self.reserved_cost:.6f} spent/reserved, "
                    f"next call worst case ${worst_case_cost:.6f}, "
                    f"cap ${self.max_cost_usd:.2f}"
                )
                raise RunAborted(self.abort_reason, self.abort_detail)
            self.calls_started += 1
            self.reserved_cost += worst_case_cost

    async def settle(self, worst_case_cost: float, actual_cost: float) -> None:
        async with self._lock:
            self.reserved_cost = max(0.0, self.reserved_cost - worst_case_cost)
            self.actual_cost += actual_cost


class _RecordingClient:
    """Count prompt/output characters around any ``LLMClient``.

    Wrapping per call keeps concurrent calls' metrics separate while still
    driving the provider client through the canonical ``InterviewChain``.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.provider = getattr(inner, "provider", "")
        self.model = getattr(inner, "model", "")
        self.prompt_chars = 0
        self.output_chars = 0
        self.first_delta_at: float | None = None

    async def astream(self, messages: list, tools: list | None = None):
        from preconsult.core.llm_stream import flatten_content

        self.prompt_chars = sum(
            len(flatten_content(getattr(message, "content", "")))
            for message in messages
        )
        if tools:
            self.prompt_chars += len(json.dumps(tools, ensure_ascii=False, default=str))
        async for delta in self._inner.astream(messages, tools):
            if self.first_delta_at is None and (delta.text or delta.tool_calls):
                self.first_delta_at = time.perf_counter()
            if delta.text:
                self.output_chars += len(delta.text)
            if delta.tool_calls:
                self.output_chars += len(
                    json.dumps(list(delta.tool_calls), ensure_ascii=False, default=str)
                )
            yield delta


class FakeLLM:
    """Deterministic local provider for offline harness runs.

    It deliberately normalizes its canned chunks through the same
    ``deltas_from_chunks`` helper the real adapters use, so the fake exercises
    tool-call merging rather than bypassing it.
    """

    provider = "fake"

    def __init__(self, model: str, questions: Sequence[str]) -> None:
        self.model = model
        self._questions = list(questions)

    async def astream(self, messages: list, tools: list | None = None):
        from langchain_core.messages import AIMessageChunk

        from preconsult.core.llm import deltas_from_chunks

        async for delta in deltas_from_chunks(self._chunks(AIMessageChunk)):
            yield delta

    def _chunks(self, message_cls: Any) -> list[Any]:
        numbered = "\n".join(
            f"{index}. {question}"
            for index, question in enumerate(self._questions, start=1)
        )
        chunks: list[Any] = [message_cls(content=numbered)]

        if self.model == "fake-text-only":
            return chunks

        if self.model == "fake-fragmented":
            arguments = json.dumps({"questions": self._questions})
            cut = len(arguments) // 2
            chunks.extend(
                [
                    message_cls(
                        content="",
                        tool_call_chunks=[
                            {
                                "name": "report_questions",
                                "args": arguments[:cut],
                                "id": "call_1",
                                "index": 0,
                            }
                        ],
                    ),
                    message_cls(
                        content="",
                        tool_call_chunks=[
                            {
                                "args": arguments[cut:],
                                "id": None,
                                "name": None,
                                "index": 0,
                            }
                        ],
                    ),
                ]
            )
            return chunks

        chunks.append(
            message_cls(
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


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark interview-question LLMs through the real service seam. "
            "Use --provider fake for the offline CI mode."
        )
    )
    parser.add_argument(
        "--provider",
        "--providers",
        dest="providers",
        default=None,
        help=(
            "Comma-separated providers: vertex, bedrock, fake. "
            "Defaults to $LLM_PROVIDER (or vertex)."
        ),
    )
    parser.add_argument(
        "--models",
        default=None,
        help=(
            "Comma-separated model ids. Defaults per provider; a live model "
            "must have an explicit price entry."
        ),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=DEFAULT_REPEAT,
        help=f"Calls per fixture per model (default {DEFAULT_REPEAT}).",
    )
    parser.add_argument(
        "--lang",
        default=DEFAULT_LANGS,
        help=f"Comma-separated fixture languages (default {DEFAULT_LANGS}).",
    )
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=DEFAULT_MAX_COST_USD,
        help=(
            "Hard estimated-cost cap in USD. The run aborts non-zero before a "
            f"call that could cross it (default {DEFAULT_MAX_COST_USD:.0f})."
        ),
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=DEFAULT_MAX_CALLS,
        help=(
            "Hard call cap. The run aborts non-zero when the plan exceeds it "
            f"(default {DEFAULT_MAX_CALLS})."
        ),
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=DEFAULT_MAX_CONCURRENCY,
        help=f"Maximum concurrent calls (default {DEFAULT_MAX_CONCURRENCY}).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=("Exact output directory. Default: outputs/llm-bench/<UTC-timestamp>/."),
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Synthetic complaint fixture JSON (default: tests/fixtures/bench).",
    )

    args = parser.parse_args(argv)
    if args.repeat < 1:
        parser.error("--repeat must be >= 1")
    if args.max_calls < 0:
        parser.error("--max-calls must be >= 0")
    if not math.isfinite(args.max_cost_usd) or args.max_cost_usd < 0:
        parser.error("--max-cost-usd must be a finite number >= 0")
    if args.max_concurrency < 1:
        parser.error("--max-concurrency must be >= 1")
    if not _csv(args.lang):
        parser.error("--lang must name at least one language")
    return args


def _prepare_environment() -> None:
    """Let the app import with harmless placeholders.

    The benchmark never serves HTTP and never creates a session, so the API key
    and cookie secret are irrelevant. They are only filled when empty, so a real
    ``.env`` still supplies credentials and ``LLM_PROVIDER``/``LLM_MODEL`` for a
    live run (``load_dotenv`` does not override existing variables).
    """
    for key in ("PRECONSULT_API_KEY", "SESSION_SECRET"):
        if not os.environ.get(key):
            os.environ[key] = "bench-offline-placeholder"


def _load_fixtures(path: Path) -> list[Fixture]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BenchConfigError(f"cannot read fixtures at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BenchConfigError(f"invalid fixture JSON at {path}: {exc}") from exc

    if payload.get("synthetic") is not True:
        raise BenchConfigError(
            f"{path} is not marked synthetic; refusing to benchmark on "
            "possibly real patient data"
        )
    complaints = payload.get("complaints")
    if not isinstance(complaints, list) or not complaints:
        raise BenchConfigError(f"{path} has no complaints list")

    fixtures: list[Fixture] = []
    seen_ids: set[str] = set()
    for item in complaints:
        if not isinstance(item, dict):
            raise BenchConfigError(f"{path} contains a non-object complaint")
        fixture_id = item.get("id")
        lang = item.get("lang")
        session = item.get("session")
        expected = item.get("expected_dimensions")
        if not isinstance(fixture_id, str) or not fixture_id:
            raise BenchConfigError(f"{path} complaint without a string id")
        if fixture_id in seen_ids:
            raise BenchConfigError(f"duplicate fixture id {fixture_id!r}")
        seen_ids.add(fixture_id)
        if lang not in ("en", "pt"):
            raise BenchConfigError(
                f"fixture {fixture_id!r} has unsupported lang {lang!r}"
            )
        if not isinstance(session, dict):
            raise BenchConfigError(f"fixture {fixture_id!r} has no session object")
        if not isinstance(expected, list) or not all(
            isinstance(dimension, str) for dimension in expected
        ):
            raise BenchConfigError(
                f"fixture {fixture_id!r} expected_dimensions must be a list of strings"
            )
        if not 3 <= len(expected) <= 5:
            raise BenchConfigError(
                f"fixture {fixture_id!r} must expect 3-5 dimensions, "
                f"got {len(expected)}"
            )
        unknown_dimensions = [
            dimension for dimension in expected if dimension not in KNOWN_DIMENSIONS
        ]
        if unknown_dimensions:
            raise BenchConfigError(
                f"fixture {fixture_id!r} has unknown dimensions {unknown_dimensions!r}"
            )
        if len(set(expected)) != len(expected):
            raise BenchConfigError(
                f"fixture {fixture_id!r} lists the same dimension twice"
            )
        fixtures.append(
            Fixture(
                id=fixture_id,
                lang=lang,
                session=dict(session),
                expected_dimensions=tuple(expected),
            )
        )
    return fixtures


def _resolve_providers(value: str | None) -> list[str]:
    providers = _csv(value) if value else [os.environ.get("LLM_PROVIDER", "vertex")]
    supported = {"vertex", "bedrock", "fake"}
    unknown = [provider for provider in providers if provider not in supported]
    if unknown:
        raise BenchConfigError(
            f"unsupported provider(s) {unknown!r}; choose from {sorted(supported)}"
        )
    return list(dict.fromkeys(providers))


def _running_in_ci() -> bool:
    return any(
        os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")
        for name in ("CI", "GITHUB_ACTIONS")
    )


def _resolve_models(
    args: argparse.Namespace, providers: Sequence[str], base_config: Any
) -> dict[str, list[str]]:
    from preconsult.core.config import validate_model_for_provider

    explicit = _csv(args.models) if args.models else []
    resolved: dict[str, list[str]] = {}
    for provider in providers:
        if explicit:
            models = list(dict.fromkeys(explicit))
        elif provider == "fake":
            models = ["fake-deterministic"]
        elif provider == base_config.provider:
            models = [base_config.model]
        else:
            models = [DEFAULT_MODELS[provider]]

        for model in models:
            if provider == "fake" and model not in FAKE_MODELS:
                raise BenchConfigError(
                    f"model {model!r} is not a fake model; choose one of "
                    f"{', '.join(FAKE_MODELS)}"
                )
            if provider != "fake":
                try:
                    validate_model_for_provider(provider, model)
                    get_price(model)
                except (UnknownModelError, ValueError) as exc:
                    raise BenchConfigError(str(exc)) from exc
        resolved[provider] = models
    return resolved


def _fake_questions(fixture: Fixture) -> list[str]:
    dimensions = list(fixture.expected_dimensions)
    if len(dimensions) < 3:
        dimensions = (dimensions + ["onset", "associated"])[:3]
    dimensions = dimensions[:5]
    bank = FAKE_QUESTION_BANK[fixture.lang]
    return [bank[dimension] for dimension in dimensions]


def _build_chain(client: Any) -> Any:
    """Build the canonical chain with a temporarily overridden provider client.

    ``get_interview_chain`` is synchronous, so this monkeypatch cannot be
    interleaved with another task in the event loop. The original singleton and
    ``get_llm`` are restored even if prompt construction raises.
    """
    from preconsult.services import agent_service

    original_get_llm = agent_service.get_llm
    original_chain = agent_service._interview_chain
    try:
        agent_service.get_llm = lambda: client
        agent_service._interview_chain = None
        return agent_service.get_interview_chain()
    finally:
        agent_service.get_llm = original_get_llm
        agent_service._interview_chain = original_chain


def _build_client_rows(
    models: dict[str, list[str]], base_config: Any
) -> dict[tuple[str, str], ClientRow]:
    from preconsult.core.config import BEDROCK_REGION, LLM_REGION, VERTEX_REGION
    from preconsult.core.errors import LLMUpstreamError
    from preconsult.core.llm import build_client

    rows: dict[tuple[str, str], ClientRow] = {}
    for provider, provider_models in models.items():
        if provider == "fake":
            for model in provider_models:
                rows[(provider, model)] = ClientRow(provider, model, None, None)
            continue

        region = LLM_REGION or (
            BEDROCK_REGION if provider == "bedrock" else VERTEX_REGION
        )
        for model in provider_models:
            config = replace(base_config, provider=provider, model=model, region=region)
            try:
                client = build_client(config)
            except LLMUpstreamError as exc:
                rows[(provider, model)] = ClientRow(
                    provider,
                    model,
                    None,
                    f"{type(exc).__name__}(kind={exc.kind})",
                )
            except Exception as exc:  # configuration/credential failure at build
                rows[(provider, model)] = ClientRow(
                    provider,
                    model,
                    None,
                    f"{type(exc).__name__}: {str(exc)[:300]}",
                )
            else:
                rows[(provider, model)] = ClientRow(provider, model, client, None)
    return rows


def _estimate_tokens(characters: int) -> int:
    return math.ceil(characters / CHARS_PER_TOKEN) if characters > 0 else 0


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    """Nearest-rank percentile (small samples; no statistics dependency)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil(percentile / 100 * len(ordered)) - 1
    return ordered[max(0, min(rank, len(ordered) - 1))]


def _score_to_dict(score: QualityScore, *, include_banned_terms: bool) -> dict:
    payload: dict[str, Any] = {
        "question_count": score.question_count,
        "count_valid": score.count_valid,
        "single_question_ratio": score.single_question_ratio,
        "language_match_ratio": score.language_match_ratio,
        "language_matches": score.language_matches,
        "duplicate_ratio": score.duplicate_ratio,
        "dimension_coverage": score.dimension_coverage,
        "covered_dimensions": list(score.covered_dimensions),
        "missing_dimensions": list(score.missing_dimensions),
    }
    if include_banned_terms:
        payload["banned_terms"] = list(score.banned_terms)
    else:
        payload["banned_term_count"] = len(score.banned_terms)
    return payload


def _failure_result(
    spec: CallSpec, error_kind: str, *, duration_ms: float = 0.0
) -> CallResult:
    return CallResult(
        provider=spec.provider,
        model=spec.model,
        lang=spec.fixture.lang,
        fixture_id=spec.fixture.id,
        repeat=spec.repeat,
        ok=False,
        error_kind=error_kind,
        ttft_ms=None,
        duration_ms=duration_ms,
        prompt_tokens_est=0,
        output_tokens_est=0,
        cost_usd_est=0.0,
        question_count=0,
        questions=None,
        score=None,
    )


async def _run_one(
    spec: CallSpec,
    client: Any,
    *,
    include_questions: bool,
) -> CallResult:
    from preconsult.core.errors import LLMUpstreamError
    from preconsult.services.agent_service import stream_interview_questions

    if spec.provider == "fake":
        inner = FakeLLM(spec.model, _fake_questions(spec.fixture))
    else:
        inner = client

    recording = _RecordingClient(inner)
    started = time.perf_counter()
    questions: list[str] = []
    error_kind: str | None = None

    try:
        chain = _build_chain(recording)
        async for event in stream_interview_questions(
            spec.fixture.session, spec.fixture.lang, chain
        ):
            if event.kind == "questions":
                questions = [str(question) for question in event.value]
    except LLMUpstreamError as exc:
        error_kind = exc.kind
    except Exception as exc:  # keep a broken call from killing the whole run
        error_kind = type(exc).__name__

    duration_ms = (time.perf_counter() - started) * 1000
    prompt_tokens = _estimate_tokens(recording.prompt_chars)
    output_tokens = _estimate_tokens(recording.output_chars)
    cost = estimate_cost_usd(spec.model, prompt_tokens, output_tokens)
    score = None
    if error_kind is None:
        score = score_questions(
            questions, spec.fixture.lang, spec.fixture.expected_dimensions
        )

    return CallResult(
        provider=spec.provider,
        model=spec.model,
        lang=spec.fixture.lang,
        fixture_id=spec.fixture.id,
        repeat=spec.repeat,
        ok=error_kind is None,
        error_kind=error_kind,
        ttft_ms=(
            (recording.first_delta_at - started) * 1000
            if recording.first_delta_at is not None
            else None
        ),
        duration_ms=duration_ms,
        prompt_tokens_est=prompt_tokens,
        output_tokens_est=output_tokens,
        cost_usd_est=cost,
        question_count=len(questions),
        questions=tuple(questions) if include_questions else None,
        score=score,
    )


def _aggregate(results: Sequence[CallResult]) -> list[AggregateRow]:
    rows: dict[tuple[str, str, str], list[CallResult]] = {}
    for result in results:
        rows.setdefault((result.provider, result.model, result.lang), []).append(result)

    aggregates: list[AggregateRow] = []
    for (provider, model, lang), group in sorted(rows.items()):
        successes = [result for result in group if result.ok]
        throttle_count = sum(1 for result in group if result.error_kind == "throttled")
        failed = sum(
            1 for result in group if not result.ok and result.error_kind != "throttled"
        )
        ttfts = [result.ttft_ms for result in successes if result.ttft_ms is not None]
        durations = [result.duration_ms for result in successes]
        quality = aggregate_quality(
            [result.score for result in successes if result.score is not None]
        )
        aggregates.append(
            AggregateRow(
                provider=provider,
                model=model,
                lang=lang,
                calls=len(group),
                ok=len(successes),
                throttled=throttle_count,
                failed=failed,
                ttft_p50_ms=_percentile(ttfts, 50),
                ttft_p95_ms=_percentile(ttfts, 95),
                duration_p50_ms=_percentile(durations, 50),
                duration_p95_ms=_percentile(durations, 95),
                prompt_tokens_est=sum(result.prompt_tokens_est for result in group),
                output_tokens_est=sum(result.output_tokens_est for result in group),
                cost_usd_est=sum(result.cost_usd_est for result in group),
                quality=quality,
            )
        )
    return aggregates


def _totals(
    aggregates: Sequence[AggregateRow],
    results: Sequence[CallResult],
    planned: int,
    tracker: BudgetTracker,
) -> dict[str, Any]:
    return {
        "calls_planned": planned,
        "calls_attempted": len(results),
        "calls_started": tracker.calls_started,
        "ok": sum(row.ok for row in aggregates),
        "throttled": sum(row.throttled for row in aggregates),
        "failed": sum(row.failed for row in aggregates),
        "error_rate": (
            sum(row.failed for row in aggregates) / len(results) if results else 0.0
        ),
        "prompt_tokens_est": sum(row.prompt_tokens_est for row in aggregates),
        "output_tokens_est": sum(row.output_tokens_est for row in aggregates),
        "cost_usd_est": sum(row.cost_usd_est for row in aggregates),
    }


def _resolve_out_dir(value: Path | None) -> Path:
    if value is not None:
        return value
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = PROJECT_ROOT / "outputs" / "llm-bench"
    candidate = base / stamp
    suffix = 1
    while candidate.exists():
        candidate = base / f"{stamp}-{suffix}"
        suffix += 1
    return candidate


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _format_ms(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "—"


def _format_pct(value: float | None) -> str:
    return f"{value:.0%}" if value is not None else "—"


def _render_report(
    *,
    document: dict[str, Any],
    aggregates: Sequence[AggregateRow],
    results: Sequence[CallResult],
    setup_errors: Sequence[dict[str, str]],
    include_sample: bool,
) -> str:
    totals = document["totals"]
    aborted = document.get("aborted")
    lines: list[str] = [
        "# LLM benchmark report",
        "",
        f"- Mode: **{document['mode']}**",
        f"- Generated: {document['generated_at']}",
        f"- Revision: `{document['revision']}`",
        f"- Fixtures: {document['fixtures']['count']} "
        f"({', '.join(f'{lang}={count}' for lang, count in document['fixtures']['by_lang'].items())})",
        f"- Calls: planned {totals['calls_planned']}, "
        f"attempted {totals['calls_attempted']}, ok {totals['ok']}",
        f"- Estimated cost: {format_usd(totals['cost_usd_est'])} "
        f"(pricing as of {PRICING_AS_OF})",
        f"- Caps: ${document['caps']['max_cost_usd']:.2f} / "
        f"{document['caps']['max_calls']} calls",
        "",
        f"**Throttled errors:** {totals['throttled']} "
        "(reported separately from real failures)",
        f"**Real failures:** {totals['failed']} "
        f"(error rate {_format_pct(totals['error_rate'])})",
        "",
    ]
    if setup_errors:
        lines.append(f"**Provider setup errors:** {len(setup_errors)}")
        lines.append("")

    if aborted:
        lines.extend(
            [
                f"**ABORTED ({aborted['reason']}):** {aborted['detail']}",
                "",
            ]
        )
    else:
        lines.extend(["**Aborted:** no", ""])

    if setup_errors:
        lines.extend(["## Provider setup errors", ""])
        for error in setup_errors:
            lines.append(
                f"- `{error['provider']}/{error['model']}`: "
                f"{_md_escape(error['error'])}"
            )
        lines.append("")

    lines.extend(
        [
            "## Latency, tokens and cost",
            "",
            "| Provider | Model | Lang | Calls | OK | Throttled | Failed | "
            "Error rate | TTFT p50 (ms) | TTFT p95 (ms) | Duration p50 (ms) | "
            "Prompt tok (est) | Output tok (est) | Cost (est) |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in aggregates:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.provider,
                    _md_escape(row.model),
                    row.lang,
                    str(row.calls),
                    str(row.ok),
                    str(row.throttled),
                    str(row.failed),
                    _format_pct(row.error_rate),
                    _format_ms(row.ttft_p50_ms),
                    _format_ms(row.ttft_p95_ms),
                    _format_ms(row.duration_p50_ms),
                    str(row.prompt_tokens_est),
                    str(row.output_tokens_est),
                    format_usd(row.cost_usd_est),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Output quality (deterministic rubric)",
            "",
            "| Provider | Model | Lang | Count 3-5 | Single Q | "
            "Language match | Duplicate | Dimension coverage | Banned rate |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in aggregates:
        quality = row.quality
        lines.append(
            "| "
            + " | ".join(
                [
                    row.provider,
                    _md_escape(row.model),
                    row.lang,
                    _format_pct(quality.get("count_valid_rate", 0.0)),
                    _format_pct(quality.get("single_question_ratio", 0.0)),
                    _format_pct(quality.get("language_match_ratio", 0.0)),
                    _format_pct(quality.get("duplicate_ratio", 0.0)),
                    _format_pct(quality.get("dimension_coverage", 0.0)),
                    _format_pct(quality.get("banned_rate", 0.0)),
                ]
            )
            + " |"
        )

    if include_sample:
        sample: list[CallResult] = []
        for lang in document["arguments"]["lang"]:
            candidates = sorted(
                (
                    result
                    for result in results
                    if result.lang == lang and result.ok and result.questions
                ),
                key=lambda item: item.fixture_id,
            )
            sample.extend(candidates[:2])
        if sample:
            lines.extend(
                [
                    "",
                    "## Synthetic sample output (fake provider)",
                    "",
                    "| Fixture | Lang | Questions |",
                    "|---|---|---|",
                ]
            )
            for result in sample:
                rendered = "<br>".join(
                    _md_escape(question) for question in result.questions or []
                )
                lines.append(
                    f"| {_md_escape(result.fixture_id)} | {result.lang} | {rendered} |"
                )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Token counts are estimated at ~4 characters/token: the LLMDelta "
            "seam does not expose provider usage metadata.",
            "- Costs use the explicit price table in `scripts/bench_pricing.py` "
            f"(as of {PRICING_AS_OF}); unknown models fail instead of guessing.",
            "- Throttled errors are counted separately from real failures: a "
            "provider rate limit is capacity information, not a quality signal.",
            "- Dimension coverage is measured against each fixture's expected "
            "OPQRST/SAMPLE dimensions. Banned rate is the fraction of calls "
            "containing a diagnosis/treatment phrase.",
        ]
    )
    if document["mode"] == "fake":
        lines.append(
            "- The fake provider is a deterministic harness self-test. Its "
            "quality numbers say nothing about a real model."
        )
    else:
        lines.append(
            "- Live mode: raw prompts and model answers are intentionally not "
            "written to this report or to run.json. Only aggregates and scores "
            "are recorded."
        )
    lines.append("")
    return "\n".join(lines)


async def _execute(
    specs: Sequence[CallSpec],
    client_rows: dict[tuple[str, str], ClientRow],
    *,
    max_calls: int,
    max_cost_usd: float,
    max_concurrency: int,
    max_output_tokens: int,
    include_questions: bool,
) -> tuple[list[CallResult], BudgetTracker, list[RunAborted]]:
    tracker = BudgetTracker(max_calls, max_cost_usd)
    semaphore = asyncio.Semaphore(max_concurrency)
    aborts: list[RunAborted] = []

    def worst_case_cost(spec: CallSpec) -> float:
        price = get_price(spec.model)
        return (
            PROMPT_TOKEN_UPPER_BOUND * price.input_per_million_usd
            + max_output_tokens * price.output_per_million_usd
        ) / 1_000_000

    async def guarded(spec: CallSpec) -> CallResult | None:
        row = client_rows[(spec.provider, spec.model)]
        async with semaphore:
            worst_case = worst_case_cost(spec)
            try:
                await tracker.reserve(worst_case)
            except RunAborted as exc:
                aborts.append(exc)
                return None
            result = _failure_result(spec, "internal")
            try:
                result = await _run_one(
                    spec, row.client, include_questions=include_questions
                )
            except Exception as exc:  # defensive: reserve must always settle
                result = _failure_result(spec, type(exc).__name__)
            finally:
                await tracker.settle(worst_case, result.cost_usd_est)
            return result

    results = await asyncio.gather(*(guarded(spec) for spec in specs))
    return [result for result in results if result is not None], tracker, aborts


def _run(args: argparse.Namespace) -> int:
    # Imports happen after _prepare_environment so config validation sees the
    # harmless placeholders rather than failing on unrelated app secrets.
    from preconsult.core.llm import config_from_env

    logging.basicConfig(level=logging.WARNING)

    fixtures = _load_fixtures(args.fixtures)
    langs = _csv(args.lang)
    unsupported = [lang for lang in langs if lang not in ("en", "pt")]
    if unsupported:
        raise BenchConfigError(
            f"unsupported language(s) {unsupported!r}; choose en, pt"
        )
    selected_fixtures = [fixture for fixture in fixtures if fixture.lang in langs]
    if not selected_fixtures:
        raise BenchConfigError(
            f"no fixtures match --lang {args.lang!r} in {args.fixtures}"
        )

    providers = _resolve_providers(args.providers)
    if "fake" in providers and len(providers) > 1:
        raise BenchConfigError(
            "the fake provider cannot be combined with live providers in one "
            "run; run the offline smoke separately"
        )
    mode = "fake" if providers == ["fake"] else "live"
    if mode == "live" and _running_in_ci():
        raise BenchConfigError(
            "live benchmark runs are refused when CI is set; use --provider fake"
        )
    base_config = config_from_env()
    models = _resolve_models(args, providers, base_config)
    client_rows = _build_client_rows(models, base_config)
    setup_errors = [
        {
            "provider": row.provider,
            "model": row.model,
            "error": row.setup_error or "",
        }
        for row in client_rows.values()
        if row.setup_error
    ]

    specs: list[CallSpec] = []
    for provider in providers:
        for model in models[provider]:
            if client_rows[(provider, model)].setup_error:
                continue
            for fixture in selected_fixtures:
                for repeat in range(args.repeat):
                    specs.append(CallSpec(provider, model, fixture, repeat))

    planned = len(specs)
    out_dir = _resolve_out_dir(args.out)
    if mode == "live":
        print(
            "LIVE MODE: this run sends synthetic fixture text to the real "
            f"provider(s) {', '.join(providers)} and may incur cost. "
            "CI must only use --provider fake.",
            file=sys.stderr,
        )

    aborted: dict[str, str] | None = None
    results: list[CallResult] = []
    tracker = BudgetTracker(args.max_calls, args.max_cost_usd)
    if planned > args.max_calls:
        aborted = {
            "reason": "max_calls",
            "detail": (
                f"planned {planned} calls exceeds --max-calls {args.max_calls}; "
                "reduce --repeat/--models/--lang or raise the cap"
            ),
        }
    else:
        results, tracker, aborts = asyncio.run(
            _execute(
                specs,
                client_rows,
                max_calls=args.max_calls,
                max_cost_usd=args.max_cost_usd,
                max_concurrency=args.max_concurrency,
                max_output_tokens=base_config.max_tokens,
                include_questions=mode == "fake",
            )
        )
        if tracker.abort_reason:
            aborted = {
                "reason": tracker.abort_reason,
                "detail": tracker.abort_detail or "",
            }
        elif aborts:
            aborted = {"reason": aborts[0].reason, "detail": aborts[0].detail}

    aggregates = _aggregate(results)
    totals = _totals(aggregates, results, planned, tracker)

    document: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "mode": mode,
        "revision": os.environ.get("GIT_SHA") or os.environ.get("K_REVISION") or "dev",
        "arguments": {
            "providers": providers,
            "models": models,
            "lang": langs,
            "repeat": args.repeat,
            "fixtures": str(args.fixtures),
            "out": str(out_dir),
        },
        "caps": {
            "max_calls": args.max_calls,
            "max_cost_usd": args.max_cost_usd,
            "max_concurrency": args.max_concurrency,
        },
        "pricing_as_of": PRICING_AS_OF,
        "fixtures": {
            "path": str(args.fixtures),
            "count": len(selected_fixtures),
            "by_lang": {
                lang: sum(1 for fixture in selected_fixtures if fixture.lang == lang)
                for lang in langs
            },
        },
        "planned_calls": planned,
        "calls_attempted": len(results),
        "setup_errors": setup_errors,
        "aborted": aborted,
        "totals": totals,
        "aggregates": [row.to_dict() for row in aggregates],
        "results": [
            result.to_dict(
                include_questions=mode == "fake",
                include_banned_terms=mode == "fake",
            )
            for result in sorted(
                results,
                key=lambda item: (
                    item.provider,
                    item.model,
                    item.lang,
                    item.fixture_id,
                    item.repeat,
                ),
            )
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run.json").write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = _render_report(
        document=document,
        aggregates=aggregates,
        results=results,
        setup_errors=setup_errors,
        include_sample=mode == "fake",
    )
    (out_dir / "report.md").write_text(report + "\n", encoding="utf-8")

    print(
        f"mode={mode} planned={planned} attempted={len(results)} "
        f"ok={totals['ok']} cost_est={format_usd(totals['cost_usd_est'])}"
    )
    print(f"throttled_errors={totals['throttled']} (reported separately)")
    print(f"real_failures={totals['failed']} error_rate={totals['error_rate']:.0%}")
    if aborted:
        print(f"aborted: {aborted['reason']}: {aborted['detail']}")
    print(f"wrote {out_dir / 'run.json'}")
    print(f"wrote {out_dir / 'report.md'}")

    if aborted:
        return 2
    if setup_errors and not results:
        return 3
    if totals["failed"] or setup_errors or totals["ok"] == 0:
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    _prepare_environment()
    try:
        return _run(args)
    except BenchConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
