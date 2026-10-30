"""
Tests for Gzip response compression.

Uses httpx.AsyncClient + ASGITransport (the suite's standard pattern) instead of
Starlette's sync TestClient, which routes through httpx and is deprecated in
favor of httpx2.
"""

import httpx
import pytest
from fastapi.responses import PlainTextResponse
from httpx import ASGITransport
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware

from preconsult.host import build_starlette_app


def _app_with_large_route():
    """A minimal app with the same GZip threshold as the served host.

    Deliberately not ``build_starlette_app()``: its SPA root mount is a
    catch-all registered last, so a route appended afterwards is shadowed
    whenever ``web/dist`` exists (CI builds it before pytest). The host's
    middleware is pinned separately by ``test_gzip_middleware_installed``.
    """
    app = Starlette()

    async def large_payload(request):
        return PlainTextResponse("A" * 1000)

    app.add_route("/test-large-payload-gzip", large_payload)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    return app


@pytest.mark.asyncio
async def test_gzip_compression_enabled():
    """Responses >= 500 bytes are gzipped when the client accepts it."""
    app = _app_with_large_route()

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/test-large-payload-gzip", headers={"Accept-Encoding": "gzip"}
        )

    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"


def test_gzip_middleware_installed():
    """GZipMiddleware must be part of the served app's stack."""
    middleware_types = [m.cls for m in build_starlette_app().user_middleware]

    assert GZipMiddleware in middleware_types
