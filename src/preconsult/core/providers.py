"""Provider/model disclosure copy for the legal pages and crawler documents.

The privacy pages and ``llms.txt`` must name the third party that actually
processes clinical text. Hardcoding that prose made it drift from the running
configuration (the pages still said "Gemini 2.5 Flash Lite" while the deployed
model was ``gemini-2.5-flash``). The phrases live here instead, keyed by
``LLM_PROVIDER`` and language, and are rendered at request time.

Only the phrases that genuinely vary are stored: the processor (provider plus
model label), the endpoint the transcript is sent to, and the retention /
training statement. The rest of the legal prose stays in the HTML documents.

This module imports no vendor SDK. It reads ``LLM_PROVIDER``/``LLM_MODEL`` from
``core.config`` at call time (not at import) so a test, or a process that
reconfigures the provider, renders the matching copy.
"""

from __future__ import annotations

from preconsult.core import config

# Model ids are provider-specific and can be long (Bedrock uses
# ``us.anthropic.claude-haiku-4-5-20251001-v1:0``). Human labels are the only
# part a reader should ever see; an id with no entry falls back to itself so a
# new model is visibly unlabelled instead of silently mislabelled.
MODEL_LABELS: dict[str, str] = {
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": "Claude Haiku 4.5",
}

# provider -> language -> phrases. ``{model}`` is filled from MODEL_LABELS.
# Keep the values short: they slot into sentences that live in the documents.
PROVIDER_DISCLOSURE: dict[str, dict[str, dict[str, str]]] = {
    "vertex": {
        "en": {
            "processor": "Google Vertex AI ({model})",
            "endpoint": "Google Vertex AI enterprise endpoints",
            "training": (
                "Data processed via enterprise Google Vertex AI is not retained "
                "by Google or used to train public machine learning models."
            ),
        },
        "pt": {
            "processor": "Google Vertex AI ({model})",
            "endpoint": "os endpoints corporativos do Google Vertex AI",
            "training": (
                "Os dados processados via Google Vertex AI não são retidos pelo "
                "Google nem utilizados para treinar modelos públicos de "
                "aprendizado de máquina."
            ),
        },
    },
    "bedrock": {
        "en": {
            "processor": (
                "Anthropic's {model}, hosted on Amazon Web Services via Amazon Bedrock"
            ),
            "endpoint": "Amazon Bedrock endpoints",
            "training": (
                "Data processed via Amazon Bedrock is not retained by Anthropic "
                "or used to train public machine learning models."
            ),
        },
        "pt": {
            "processor": (
                "{model}, da Anthropic, hospedado na Amazon Web Services "
                "via Amazon Bedrock"
            ),
            "endpoint": "os endpoints do Amazon Bedrock",
            "training": (
                "Os dados processados via Amazon Bedrock não são retidos pela "
                "Anthropic nem utilizados para treinar modelos públicos de "
                "aprendizado de máquina."
            ),
        },
    },
}

DEFAULT_LANG = "en"


def resolve_model_label(model_id: str) -> str:
    """Return the human label for ``model_id``, or the id itself when unknown."""
    return MODEL_LABELS.get(model_id, model_id)


def _resolve_lang(lang: str | None) -> str:
    """Mirror the site rule: anything starting with ``pt`` is Portuguese."""
    return "pt" if (lang or "").lower().startswith("pt") else DEFAULT_LANG


def active_disclosure(
    lang: str | None = DEFAULT_LANG,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, str]:
    """Return the disclosure phrases for the configured (or given) provider.

    ``provider``/``model`` default to ``LLM_PROVIDER``/``LLM_MODEL`` at call
    time, so flipping the configuration flips the copy without restarting a
    render path or editing HTML. An unknown provider is a programming error
    (``config`` validates the variable), so it raises rather than falling back
    to a provider that is not actually receiving the data.
    """
    provider_id = (provider or config.LLM_PROVIDER).strip().lower()
    row = PROVIDER_DISCLOSURE.get(provider_id)
    if row is None:
        raise ValueError(
            f"no disclosure copy for LLM provider {provider_id!r}; "
            f"known providers: {sorted(PROVIDER_DISCLOSURE)}"
        )

    # A missing language row falls back to English, as everywhere else in the
    # app; a missing model label falls back to the raw id (see above).
    phrases = row.get(_resolve_lang(lang)) or row[DEFAULT_LANG]
    label = resolve_model_label(model or config.LLM_MODEL)
    return {
        "processor": phrases["processor"].format(model=label),
        "endpoint": phrases["endpoint"],
        "training": phrases["training"],
    }
