"""Price table for the offline LLM benchmark harness.

The table is deliberately explicit: a model id that is not listed raises
:class:`UnknownModelError` instead of falling back to a guessed price. Prices
are public list prices in USD per **one million** tokens, recorded on
``PRICING_AS_OF``. They are budgeting inputs, not an invoice: providers change
prices, regions differ, and the harness prices provider-reported counts when
the stream exposes them, falling back to character estimates otherwise; treat
the result as a budgeting input, not an invoice.

Add a model by adding one :class:`ModelPrice` entry and a test for it. Live
runs refuse to start when any requested model is missing, so a silent guess can
never inflate or hide the reported cost.
"""

from __future__ import annotations

from dataclasses import dataclass

PRICING_AS_OF = "2026-11-02"


class UnknownModelError(ValueError):
    """Raised when a model id has no explicit price entry."""


@dataclass(frozen=True)
class ModelPrice:
    """Public list price for one model, in USD per million tokens."""

    model: str
    input_per_million_usd: float
    output_per_million_usd: float
    as_of: str = PRICING_AS_OF
    source: str = "public list price; verify with the provider before relying on it"


def _price(
    model: str,
    input_per_million_usd: float,
    output_per_million_usd: float,
    *,
    source: str = "public list price; verify with the provider before relying on it",
) -> ModelPrice:
    return ModelPrice(
        model=model,
        input_per_million_usd=input_per_million_usd,
        output_per_million_usd=output_per_million_usd,
        as_of=PRICING_AS_OF,
        source=source,
    )


# Keys are the exact model ids the app sends to a provider. Keep the fake
# models at zero so an offline smoke run can never trip the cost cap.
PRICES: dict[str, ModelPrice] = {
    "gemini-2.5-flash": _price("gemini-2.5-flash", 0.30, 2.50),
    "gemini-2.5-flash-lite": _price("gemini-2.5-flash-lite", 0.10, 0.40),
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": _price(
        "us.anthropic.claude-haiku-4-5-20251001-v1:0", 1.00, 5.00
    ),
    "us.anthropic.claude-3-5-haiku-20241022-v1:0": _price(
        "us.anthropic.claude-3-5-haiku-20241022-v1:0", 0.80, 4.00
    ),
    # Deterministic local providers used by the offline harness. They make no
    # network calls and consume no billable tokens.
    "fake-deterministic": _price("fake-deterministic", 0.0, 0.0),
    "fake-fragmented": _price("fake-fragmented", 0.0, 0.0),
    "fake-text-only": _price("fake-text-only", 0.0, 0.0),
}

FAKE_MODELS: tuple[str, ...] = (
    "fake-deterministic",
    "fake-fragmented",
    "fake-text-only",
)


def get_price(model: str) -> ModelPrice:
    """Return the explicit price entry for ``model``.

    Raises:
        UnknownModelError: if the model is not in :data:`PRICES`. The message
            names the model and the table's ``as_of`` date and lists known ids,
            so the fix is a one-line table update rather than a guess.
    """
    try:
        return PRICES[model]
    except KeyError:
        known = ", ".join(sorted(PRICES))
        raise UnknownModelError(
            f"No price for model {model!r} as of {PRICING_AS_OF}. "
            "Refusing to guess: add an explicit entry to "
            "scripts/bench_pricing.py PRICES. "
            f"Known models: {known}."
        ) from None


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a call from token counts.

    Token counts below zero are a programming error and raise ``ValueError``;
    an unknown model raises :class:`UnknownModelError`.
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    price = get_price(model)
    return (
        input_tokens * price.input_per_million_usd
        + output_tokens * price.output_per_million_usd
    ) / 1_000_000


def format_usd(value: float) -> str:
    """Format a tiny per-call cost without collapsing it to ``$0.00``."""
    return f"${value:,.6f}"


__all__ = [
    "FAKE_MODELS",
    "PRICES",
    "PRICING_AS_OF",
    "ModelPrice",
    "UnknownModelError",
    "estimate_cost_usd",
    "format_usd",
    "get_price",
]
