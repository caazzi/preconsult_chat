"""Crawler-facing text documents (``robots.txt``, ``sitemap.xml``, ``llms.txt``).

These were string literals inside the Reflex host module. They are plain text
with no framework dependency, so they live here as pure render functions: the
Reflex app calls them today, and the post-cutover FastAPI app will call the
same functions unchanged.

``sitemap_xml`` takes the date as a parameter instead of reading the clock, so
the output is deterministic in tests.
"""

from __future__ import annotations

from datetime import date

SITE_URL = "https://pre-consult.org"

ROBOTS_TXT = (
    "User-agent: *\n"
    "Disallow: /admin/\n"
    "Disallow: /api/\n"
    "Allow: /\n\n"
    f"Sitemap: {SITE_URL}/sitemap.xml\n"
)

LLMS_TXT = (
    "# PreConsult — AI Medical Intake Assistant\n\n"
    "> Privacy-first guided AI interview helper for patient intake. "
    "Zero data persistence. No account required.\n\n"
    "PreConsult helps patients organize symptoms and prepare for "
    "doctor's appointments through a structured multi-step intake form. "
    "The entire process runs in-browser, uses Google Vertex AI (Gemini) "
    "to generate targeted clinical questions, and produces a "
    "downloadable PDF report. All data is deleted when the browser tab is closed.\n\n"
    "Key principles:\n"
    "- Zero data persistence: No data stored on servers after session ends\n"
    "- No account required: Fully anonymous usage\n"
    "- AI-powered clinical questions via Google Vertex AI (Gemini 2.5 Flash Lite)\n"
    "- Multi-language: English and Portuguese (Brazil)\n"
    "- PDF report generation with form data and Q&A\n"
    "- Privacy-first: No tracking, no cookies, no PII collected\n\n"
    "## Pages\n\n"
    f"- [Homepage]({SITE_URL}/): Main intake form with 6-step wizard\n"
)


def sitemap_xml(today: date | None = None) -> str:
    """Render the sitemap with the given (or current) ``lastmod`` date."""
    lastmod = (today or date.today()).isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        "  <url>\n"
        f"    <loc>{SITE_URL}/</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        "    <changefreq>weekly</changefreq>\n"
        "    <priority>1.0</priority>\n"
        f'    <xhtml:link rel="alternate" hreflang="en" href="{SITE_URL}/?lang=en"/>\n'
        f'    <xhtml:link rel="alternate" hreflang="pt" href="{SITE_URL}/?lang=pt"/>\n'
        f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_URL}/"/>\n'
        "  </url>\n"
        "  <url>\n"
        f"    <loc>{SITE_URL}/?lang=pt</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        "    <changefreq>weekly</changefreq>\n"
        "    <priority>0.9</priority>\n"
        f'    <xhtml:link rel="alternate" hreflang="pt" href="{SITE_URL}/?lang=pt"/>\n'
        f'    <xhtml:link rel="alternate" hreflang="en" href="{SITE_URL}/?lang=en"/>\n'
        f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_URL}/"/>\n'
        "  </url>\n"
        "</urlset>\n"
    )
