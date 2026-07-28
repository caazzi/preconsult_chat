"""
Tests for Gzip response compression and static asset caching headers.
"""
from fastapi.testclient import TestClient
from fastapi.responses import PlainTextResponse
from reflex_app.preconsult.preconsult import app


def test_gzip_compression_enabled():
    """Verify that GZipMiddleware compresses responses >= 500 bytes when Accept-Encoding: gzip is sent."""
    starlette_app = app._api

    async def large_payload(request):
        return PlainTextResponse("A" * 1000)

    starlette_app.add_route("/test-large-payload-gzip", large_payload)

    client = TestClient(starlette_app)
    response = client.get("/test-large-payload-gzip", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"


def test_gzip_middleware_installed():
    """Verify that GZipMiddleware is present in FastAPI/Starlette middleware stack."""
    from starlette.middleware.gzip import GZipMiddleware
    starlette_app = app._api
    middleware_types = [m.cls for m in starlette_app.user_middleware]
    assert GZipMiddleware in middleware_types
