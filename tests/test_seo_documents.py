"""Crawler-facing documents stay byte-identical after the extraction.

``robots.txt``, ``sitemap.xml`` and ``llms.txt`` were inline literals in the
old host module; they now come from ``preconsult.site.seo``, which has no
framework dependency. These
tests check the served contract (status, media type, cache headers, content)
and the deterministic sitemap rendering.
"""

from datetime import date

import httpx
import pytest
from httpx import ASGITransport

from preconsult.site.seo import LLMS_TXT, ROBOTS_TXT, SITE_URL, sitemap_xml
from preconsult.host import app


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_robots_txt_contract():
    async with _client() as client:
        resp = await client.get("/robots.txt")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.headers["cache-control"] == "public, max-age=86400"
    assert resp.text == ROBOTS_TXT
    assert "Disallow: /api/" in resp.text
    assert "Disallow: /admin/" in resp.text
    assert f"Sitemap: {SITE_URL}/sitemap.xml" in resp.text


@pytest.mark.asyncio
async def test_sitemap_xml_contract():
    async with _client() as client:
        resp = await client.get("/sitemap.xml")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert resp.headers["cache-control"] == "public, max-age=86400"
    assert resp.text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert f"<lastmod>{date.today().isoformat()}</lastmod>" in resp.text
    # Both language alternates and the x-default fallback must be declared.
    assert 'hreflang="pt"' in resp.text
    assert 'hreflang="en"' in resp.text
    assert 'hreflang="x-default"' in resp.text


@pytest.mark.asyncio
async def test_llms_txt_contract():
    async with _client() as client:
        resp = await client.get("/llms.txt")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert resp.headers["cache-control"] == "public, max-age=3600"
    assert resp.text == LLMS_TXT
    assert resp.text.startswith("# PreConsult")


def test_sitemap_is_deterministic_for_a_given_date():
    rendered = sitemap_xml(date(2026, 1, 2))

    assert rendered.count("<lastmod>2026-01-02</lastmod>") == 2
    assert rendered.rstrip().endswith("</urlset>")


def test_sitemap_is_well_formed_xml():
    import xml.etree.ElementTree as ET

    root = ET.fromstring(sitemap_xml(date(2026, 1, 2)))

    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locs = [node.text for node in root.iter(f"{ns}loc")]
    assert locs == [f"{SITE_URL}/", f"{SITE_URL}/?lang=pt"]
