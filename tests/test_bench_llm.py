"""Focused tests for the benchmark harness plumbing (no live provider calls).

The fake provider is exercised here as a client; the full harness smoke run is
the `scripts/bench_llm.py --provider fake` gate command.
"""

import json
from pathlib import Path

import pytest

from preconsult.core.llm import LLMDelta
from scripts import bench_llm

FIXTURE = bench_llm._load_fixtures(bench_llm.DEFAULT_FIXTURES)[0]


class _StubLLM:
    """Minimal provider that drives ``_run_one`` through the real seam."""

    provider = "fake"
    model = "gemini-2.5-flash"

    def __init__(self, usage: dict | None) -> None:
        self._usage = usage

    async def astream(self, messages, tools=None):
        yield LLMDelta(text="1. When did it start?\n2. Does it spread?")
        if self._usage is not None:
            yield LLMDelta(usage=dict(self._usage))


async def test_call_cap_aborts_before_an_extra_call():
    tracker = bench_llm.BudgetTracker(max_calls=1, max_cost_usd=10.0)

    await tracker.reserve(0.0)

    with pytest.raises(bench_llm.RunAborted) as exc_info:
        await tracker.reserve(0.0)

    assert exc_info.value.reason == "max_calls"
    assert tracker.abort_reason == "max_calls"
    assert tracker.calls_started == 1


async def test_cost_cap_aborts_before_a_call_that_could_cross_it():
    tracker = bench_llm.BudgetTracker(max_calls=10, max_cost_usd=0.001)

    with pytest.raises(bench_llm.RunAborted) as exc_info:
        await tracker.reserve(0.002)

    assert exc_info.value.reason == "max_cost_usd"
    assert tracker.calls_started == 0


async def test_settling_releases_the_reservation_and_records_actual_cost():
    tracker = bench_llm.BudgetTracker(max_calls=10, max_cost_usd=0.010)

    await tracker.reserve(0.006)
    await tracker.settle(0.006, 0.001)

    assert tracker.reserved_cost == 0.0
    assert tracker.actual_cost == 0.001
    # The remaining headroom is real, not shadowed by the old reservation.
    await tracker.reserve(0.005)
    assert tracker.calls_started == 2


def test_token_estimate_and_percentiles_are_deterministic():
    assert bench_llm._estimate_tokens(0) == 0
    assert bench_llm._estimate_tokens(1) == 1
    assert bench_llm._estimate_tokens(8) == 2
    assert bench_llm._percentile([], 50) is None
    assert bench_llm._percentile([30.0, 10.0, 20.0], 50) == 20.0
    assert bench_llm._percentile([10.0, 20.0, 30.0, 40.0], 95) == 40.0


@pytest.mark.parametrize(
    "model", ["fake-deterministic", "fake-fragmented", "fake-text-only"]
)
async def test_fake_llm_is_deterministic_for_every_shape(model):
    questions = ["When did it start?", "What makes it worse?", "Does it spread?"]
    client = bench_llm.FakeLLM(model, questions)

    first = [delta async for delta in client.astream([], None)]
    second = [delta async for delta in client.astream([], None)]

    assert first == second
    assert "When did it start?" in "".join(delta.text for delta in first)
    assert first[-1].usage == bench_llm.FAKE_USAGE
    if model == "fake-text-only":
        assert not any(delta.tool_calls for delta in first)
    else:
        emitted = [call for delta in first for call in delta.tool_calls]
        assert emitted[0]["args"]["questions"] == questions


async def test_provider_usage_drives_tokens_and_cost():
    spec = bench_llm.CallSpec("vertex", "gemini-2.5-flash", FIXTURE, 0)
    client = _StubLLM(
        {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read": 250}
    )

    result = await bench_llm._run_one(spec, client, include_questions=False)

    assert result.ok
    assert result.tokens_source == "exact"
    assert result.prompt_tokens == 1_000_000
    assert result.output_tokens == 1_000_000
    assert result.cache_read_tokens == 250
    # gemini-2.5-flash list price: $0.30 input + $2.50 output per million.
    # A character estimate would be orders of magnitude below this.
    assert result.cost_usd == pytest.approx(2.80)


async def test_missing_usage_falls_back_to_estimates_and_labels_them():
    spec = bench_llm.CallSpec("vertex", "gemini-2.5-flash", FIXTURE, 0)

    result = await bench_llm._run_one(spec, _StubLLM(None), include_questions=False)

    assert result.ok
    assert result.tokens_source == "estimated"
    assert result.prompt_tokens > 0
    assert result.output_tokens > 0
    assert result.cache_read_tokens is None
    assert result.cost_usd == pytest.approx(
        bench_llm.estimate_cost_usd(
            spec.model, result.prompt_tokens, result.output_tokens
        )
    )


async def test_fake_provider_reports_exact_usage():
    spec = bench_llm.CallSpec("fake", "fake-deterministic", FIXTURE, 0)

    result = await bench_llm._run_one(spec, None, include_questions=False)

    assert result.ok
    assert result.tokens_source == "exact"
    assert result.prompt_tokens == bench_llm.FAKE_USAGE["input_tokens"]
    assert result.output_tokens == bench_llm.FAKE_USAGE["output_tokens"]


def test_fixture_loader_refuses_non_synthetic_data(tmp_path: Path):
    path = tmp_path / "real.json"
    path.write_text(
        json.dumps({"synthetic": False, "complaints": []}), encoding="utf-8"
    )

    with pytest.raises(bench_llm.BenchConfigError, match="not marked synthetic"):
        bench_llm._load_fixtures(path)


def test_fixture_loader_accepts_the_committed_synthetic_file():
    fixtures = bench_llm._load_fixtures(bench_llm.DEFAULT_FIXTURES)

    assert len(fixtures) == 20
    assert {fixture.lang for fixture in fixtures} == {"en", "pt"}
    assert all(fixture.session.get("chief_complaint") for fixture in fixtures)
