"""Composition contract of the Reflex-free host (`preconsult.host`).

The Reflex host is still the deployed app, but this one is what replaces it —
so the properties that must survive the cutover are pinned here rather than
inherited from tests that will be deleted with `reflex_app/`:

* registration order (`/api` first, SPA mount last, so the catch-all never
  shadows an API or document route);
* the middleware order (bot gate outermost, then request id);
* the root mount's 404 semantics (a stale ``/_event`` probe or a scanner must
  never receive the SPA shell);
* ``x-request-id`` on every response and the ``static.asset_404`` counter;
* ``/health`` reporting ``not_configured`` when nothing owns a socket.
"""

import httpx
import pytest
from httpx import ASGITransport

from preconsult.core.observability import snapshot_counters
from preconsult.host import build_asgi_app, build_starlette_app, resolve_spa_dist
from preconsult.site.static import SPAStaticFiles

SHELL = '<!doctype html><html><body><div id="root"></div></body></html>'
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
)


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "index.html").write_text(SHELL)
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log(1)")
    return tmp_path


def _client(app):
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------
def test_spa_mount_is_last_so_it_cannot_shadow_api_or_documents(dist):
    routes = build_starlette_app(spa_dist=dist).routes

    paths = [getattr(route, "path", None) for route in routes]
    # Starlette normalises a root mount to path "", which is also why the
    # document contract checks for "." rather than "" (see SPAStaticFiles).
    assert paths.index("/api") < paths.index("/health")
    assert paths[-1] == ""
    assert isinstance(routes[-1].app, SPAStaticFiles)
    assert paths.index("/privacy") < len(routes) - 1


def test_no_root_mount_when_the_bundle_is_missing(tmp_path):
    routes = build_starlette_app(spa_dist=tmp_path / "does-not-exist").routes

    assert not any(
        isinstance(getattr(route, "app", None), SPAStaticFiles) for route in routes
    )


def test_resolve_spa_dist_honours_the_override(monkeypatch, dist):
    monkeypatch.setenv("WEB_DIST_DIR", str(dist))

    assert resolve_spa_dist() == dist


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bot_gate_blocks_scanner_user_agents(dist):
    async with _client(build_asgi_app(spa_dist=dist)) as client:
        resp = await client.post(
            "/api/session/init", json={}, headers={"user-agent": "curl/8.0"}
        )

    assert resp.status_code == 403
    assert resp.json()["code"] == "bot_blocked"


@pytest.mark.asyncio
async def test_browser_user_agents_reach_the_api(dist):
    async with _client(build_asgi_app(spa_dist=dist)) as client:
        resp = await client.post(
            "/api/session/init", json={}, headers={"user-agent": BROWSER_UA}
        )

    assert resp.status_code == 403
    assert resp.json()["code"] == "auth_failed"


@pytest.mark.asyncio
async def test_every_response_carries_a_request_id(dist):
    async with _client(build_asgi_app(spa_dist=dist)) as client:
        resp = await client.get("/health/live")

    assert resp.status_code == 200
    assert resp.headers.get("x-request-id")


# ---------------------------------------------------------------------------
# Root-mount semantics
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stale_socket_probe_never_receives_the_shell(dist):
    async with _client(build_asgi_app(spa_dist=dist)) as client:
        for path in ("/_event", "/_event/", "/_ping", "/_upload/x"):
            resp = await client.get(path)
            assert resp.status_code == 404, path
            assert resp.headers["content-type"].startswith("text/plain"), path


@pytest.mark.asyncio
async def test_unknown_navigation_serves_the_shell_no_store(dist):
    async with _client(build_asgi_app(spa_dist=dist)) as client:
        resp = await client.get("/some/deep/link")

    assert resp.status_code == 200
    assert SHELL in resp.text
    assert "no-store" in resp.headers["cache-control"]
    assert "immutable" not in resp.headers["cache-control"]


@pytest.mark.asyncio
async def test_missing_asset_is_a_404_and_is_counted(dist):
    before = snapshot_counters().get("static.asset_404", 0)

    async with _client(build_asgi_app(spa_dist=dist)) as client:
        resp = await client.get("/assets/missing.js")

    assert resp.status_code == 404
    assert snapshot_counters().get("static.asset_404", 0) == before + 1


@pytest.mark.asyncio
async def test_hashed_asset_is_immutable(dist):
    async with _client(build_asgi_app(spa_dist=dist)) as client:
        resp = await client.get("/assets/app.js")

    assert resp.status_code == 200
    assert "immutable" in resp.headers["cache-control"]


# ---------------------------------------------------------------------------
# Health without a socket
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_reports_not_configured_without_a_probe(dist):
    async with _client(build_asgi_app(spa_dist=dist)) as client:
        payload = (await client.get("/health")).json()

    assert payload["event_channel"] == "not_configured"
