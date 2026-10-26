"""Crawler and legal routes, registered on any Starlette/FastAPI app.

These were registered inline in the Reflex host. The bodies already live in
``site.seo`` / ``site.legal``; this module only wires them, so the cutover can
keep serving them without touching Reflex.
"""

from __future__ import annotations

from starlette.responses import Response

from preconsult.site.legal import legal_page_endpoint
from preconsult.site.seo import LLMS_TXT, ROBOTS_TXT
from preconsult.site.seo import sitemap_xml as render_sitemap_xml


async def robots_txt(request):
    return Response(
        content=ROBOTS_TXT,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=86400"},
    )


async def sitemap_xml(request):
    return Response(
        content=render_sitemap_xml(),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


async def llms_txt(request):
    return Response(
        content=LLMS_TXT,
        media_type="text/markdown",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def register_site_routes(app) -> None:
    """Register the crawler documents and the legal pages.

    Registration order matches the monolith (crawler documents, then legal), and
    every route stays out of the OpenAPI schema.
    """
    app.add_route("/robots.txt", robots_txt, include_in_schema=False, methods=["GET"])
    app.add_route("/sitemap.xml", sitemap_xml, include_in_schema=False, methods=["GET"])
    app.add_route("/llms.txt", llms_txt, include_in_schema=False, methods=["GET"])
    app.add_route(
        "/privacy",
        legal_page_endpoint("privacy"),
        include_in_schema=False,
        methods=["GET"],
    )
    app.add_route(
        "/terms",
        legal_page_endpoint("terms"),
        include_in_schema=False,
        methods=["GET"],
    )
