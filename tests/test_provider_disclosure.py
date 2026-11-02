"""The served provider disclosure follows configuration, not stale prose.

The privacy pages and ``llms.txt`` used to hardcode "Google Vertex AI (Gemini
2.5 Flash Lite)" while ``LLM_MODEL`` actually selected ``gemini-2.5-flash``.
These tests pin that the disclosure comes from ``core/providers.py`` for the
configured provider, that switching providers cannot leave the other
provider's name behind, and that a model id from configuration cannot inject
markup into the page.
"""

from __future__ import annotations

import re

import httpx
import pytest
from httpx import ASGITransport

from preconsult.core import config
from preconsult.core.providers import (
    active_disclosure,
    resolve_model_label,
)
from preconsult.host import app
from preconsult.site.legal import legal_dir
from preconsult.site.seo import render_llms_txt

PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}")
LEGAL_LANGS = ("en", "pt")

# Expected rendered copy. Kept as literals (not read back from the module) so a
# wrong phrase in PROVIDER_DISCLOSURE fails the test instead of moving with it.
PROVIDER_CASES = {
    "vertex": {
        "model": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "en": "Google Vertex AI (Gemini 2.5 Flash)",
        "pt": "Google Vertex AI (Gemini 2.5 Flash)",
        "endpoint": {
            "en": "Google Vertex AI enterprise endpoints",
            "pt": "os endpoints corporativos do Google Vertex AI",
        },
        "training": {
            "en": "Data processed via enterprise Google Vertex AI is not retained by Google",
            "pt": "Os dados processados via Google Vertex AI não são retidos pelo Google",
        },
        "absent": ("Anthropic", "Amazon Bedrock"),
    },
    "bedrock": {
        "model": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "label": "Claude Haiku 4.5",
        "en": (
            "Anthropic's Claude Haiku 4.5, hosted on Amazon Web Services via "
            "Amazon Bedrock"
        ),
        "pt": (
            "Claude Haiku 4.5, da Anthropic, hospedado na Amazon Web Services "
            "via Amazon Bedrock"
        ),
        "endpoint": {
            "en": "Amazon Bedrock endpoints",
            "pt": "os endpoints do Amazon Bedrock",
        },
        "training": {
            "en": "Data processed via Amazon Bedrock is not retained by Anthropic",
            "pt": "Os dados processados via Amazon Bedrock não são retidos pela Anthropic",
        },
        "absent": ("Google Vertex AI", "Gemini"),
    },
}
CASE_IDS = list(PROVIDER_CASES)


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
@pytest.mark.parametrize("lang", LEGAL_LANGS)
@pytest.mark.parametrize("provider, case", PROVIDER_CASES.items(), ids=CASE_IDS)
async def test_privacy_page_follows_the_configured_provider(
    monkeypatch, provider, case, lang
):
    monkeypatch.setattr(config, "LLM_PROVIDER", provider)
    monkeypatch.setattr(config, "LLM_MODEL", case["model"])

    async with _client() as client:
        resp = await client.get(f"/privacy?lang={lang}")

    assert resp.status_code == 200
    assert case[lang] in resp.text
    assert case["label"] in resp.text
    assert case["endpoint"][lang] in resp.text
    assert case["training"][lang] in resp.text
    # The human label is what readers see; the provider-specific model id is not.
    assert case["model"] not in resp.text
    for other_provider in case["absent"]:
        assert other_provider not in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("provider, case", PROVIDER_CASES.items(), ids=CASE_IDS)
async def test_llms_txt_follows_the_configured_provider(monkeypatch, provider, case):
    monkeypatch.setattr(config, "LLM_PROVIDER", provider)
    monkeypatch.setattr(config, "LLM_MODEL", case["model"])

    async with _client() as client:
        resp = await client.get("/llms.txt")

    assert resp.status_code == 200
    assert case["en"] in resp.text
    assert case["label"] in resp.text
    for other_provider in case["absent"]:
        assert other_provider not in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("lang", LEGAL_LANGS)
async def test_no_served_page_has_an_unrendered_placeholder(lang):
    async with _client() as client:
        pages = [
            (await client.get(f"/privacy?lang={lang}")).text,
            (await client.get(f"/terms?lang={lang}")).text,
            (await client.get("/llms.txt")).text,
        ]

    for text in pages:
        assert PLACEHOLDER.search(text) is None


@pytest.mark.parametrize("lang", LEGAL_LANGS)
def test_privacy_documents_reference_every_disclosure_placeholder(lang):
    """A document that stops referencing the disclosure must fail loudly."""
    raw = (legal_dir() / f"privacy.{lang}.html").read_text(encoding="utf-8")

    assert "{{LLM_PROCESSOR}}" in raw
    assert "{{LLM_ENDPOINT}}" in raw
    assert "{{LLM_TRAINING}}" in raw


def test_model_label_falls_back_to_the_raw_id():
    assert resolve_model_label("some-future-model-v2") == "some-future-model-v2"
    assert resolve_model_label("gemini-2.5-flash") == "Gemini 2.5 Flash"


def test_unknown_language_falls_back_to_english():
    en = active_disclosure("en", provider="vertex", model="gemini-2.5-flash")
    fr = active_disclosure("fr", provider="vertex", model="gemini-2.5-flash")
    pt_br = active_disclosure("pt-BR", provider="vertex", model="gemini-2.5-flash")
    pt = active_disclosure("pt", provider="vertex", model="gemini-2.5-flash")

    assert fr == en
    assert pt_br == pt
    assert pt != en


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="no disclosure copy"):
        active_disclosure("en", provider="openai", model="gpt-4")


@pytest.mark.asyncio
async def test_model_id_with_markup_is_escaped_in_the_served_page(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "vertex")
    monkeypatch.setattr(config, "LLM_MODEL", "<script>alert(1)</script>")

    async with _client() as client:
        resp = await client.get("/privacy?lang=en")

    assert resp.status_code == 200
    assert "<script>alert(1)</script>" not in resp.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in resp.text


def test_llms_txt_render_uses_the_configured_disclosure(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "bedrock")
    monkeypatch.setattr(
        config, "LLM_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )

    rendered = render_llms_txt()

    assert "Anthropic's Claude Haiku 4.5" in rendered
    assert "Google Vertex AI" not in rendered
