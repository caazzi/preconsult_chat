"""The legal pages survive the Reflex → SPA cutover unchanged.

Privacy/terms used to be ~300 lines of inline HTML inside the Reflex host
module. They now come from ``web/legal/<page>.<lang>.html`` through a
Reflex-free module, but the public contract must not change: same URLs, same
language negotiation (``?lang=`` then the ``preconsult_lang`` cookie), same
canonical links. These tests pin that, plus the packaging assumption that the
four documents actually ship.
"""

import httpx
import pytest
from httpx import ASGITransport

from preconsult.site.legal import (
    LANG_COOKIE,
    LEGAL_LANGUAGES,
    LEGAL_PAGES,
    legal_dir,
    legal_html,
    resolve_lang,
)
from preconsult.host import app


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
@pytest.mark.parametrize("page", LEGAL_PAGES)
async def test_page_defaults_to_english(page):
    async with _client() as client:
        resp = await client.get(f"/{page}")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert '<html lang="en">' in resp.text
    assert f'<link rel="canonical" href="https://pre-consult.org/{page}"' in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("page", LEGAL_PAGES)
async def test_query_lang_selects_portuguese(page):
    async with _client() as client:
        resp = await client.get(f"/{page}?lang=pt")

    assert resp.status_code == 200
    assert '<html lang="pt">' in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("page", LEGAL_PAGES)
async def test_cookie_lang_selects_portuguese(page):
    async with _client() as client:
        client.cookies.set(LANG_COOKIE, "pt")
        resp = await client.get(f"/{page}")

    assert resp.status_code == 200
    assert '<html lang="pt">' in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("page", LEGAL_PAGES)
async def test_query_lang_overrides_cookie(page):
    async with _client() as client:
        client.cookies.set(LANG_COOKIE, "pt")
        resp = await client.get(f"/{page}?lang=en")

    assert resp.status_code == 200
    assert '<html lang="en">' in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("page", LEGAL_PAGES)
async def test_both_languages_are_served(page):
    async with _client() as client:
        en = await client.get(f"/{page}?lang=en")
        pt = await client.get(f"/{page}?lang=pt")

    assert en.text != pt.text
    assert "Privacy" in en.text or "Terms" in en.text
    assert "Privacidade" in pt.text or "Termos" in pt.text


def test_resolve_lang_matches_the_old_rules():
    assert resolve_lang(None, None) == "en"
    assert resolve_lang("", "") == "en"
    assert resolve_lang("pt-BR", None) == "pt"
    assert resolve_lang(None, "PT") == "pt"
    assert resolve_lang("en", "pt") == "en"
    # Anything unrecognised falls back to English rather than 404ing.
    assert resolve_lang("fr", None) == "en"


def test_every_document_is_packaged():
    directory = legal_dir()
    for page in LEGAL_PAGES:
        for lang in LEGAL_LANGUAGES:
            path = directory / f"{page}.{lang}.html"
            assert path.is_file(), f"missing {path}"
            html = legal_html(page, lang)
            assert html.lstrip().startswith("<!DOCTYPE html>")
            assert html.rstrip().endswith("</html>")
            assert f'<html lang="{lang}">' in html
            # Guards against a half-written extraction.
            assert len(html) > 4000


def test_unknown_page_or_language_is_rejected():
    with pytest.raises(ValueError):
        legal_html("cookies", "en")
    with pytest.raises(ValueError):
        legal_html("privacy", "fr")
