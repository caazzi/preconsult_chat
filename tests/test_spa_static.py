"""Caching + fallback contract of the SPA static mount.

The mount is exercised at ``/next`` in the fixtures below and at ``/`` in the
``root_client`` fixture: after the cutover it is the root mount, and the
semantics must be identical either way.

A client-side router needs unknown *navigation* routes to fall back to
``index.html``, but a missing *file* must stay a 404: serving HTML for a missing
hashed asset — and letting it be cached ``immutable`` — is how a partial deploy
turns into "Unexpected token '<'" and a poisoned browser/CDN cache.

After the cutover the same class is mounted at ``/`` and inherits the origin's
404 semantics, so scanner probes and Reflex backend prefixes must stay plain
404s (never the shell). Those cases are exercised through a root mount.
"""

import logging

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from preconsult.site.static import SPAStaticFiles

SHELL = "<html>shell</html>"
PT_SHELL = "<html>shell-pt</html>"
ASSET_BODY = "console.log(1)"


def _build_dist(tmp_path, *, portuguese: bool = True):
    (tmp_path / "index.html").write_text(SHELL)
    if portuguese:
        (tmp_path / "index.pt.html").write_text(PT_SHELL)
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text(ASSET_BODY)
    return tmp_path


@pytest.fixture()
def client(tmp_path):
    app = Starlette()
    app.mount("/next", SPAStaticFiles(directory=str(_build_dist(tmp_path)), html=True))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def root_client(tmp_path):
    """The post-cutover shape: the SPA owns ``/``."""
    app = Starlette()
    app.mount("/", SPAStaticFiles(directory=str(_build_dist(tmp_path)), html=True))
    with TestClient(app) as test_client:
        yield test_client


def test_index_is_served_no_store(client):
    response = client.get("/next/")

    assert response.status_code == 200
    assert "shell" in response.text
    cache_control = response.headers["cache-control"]
    assert "no-store" in cache_control
    assert "immutable" not in cache_control


def test_lang_pt_is_answered_with_the_portuguese_document(root_client):
    """`/?lang=pt` is the crawler/hreflang URL for the pt landing."""
    response = root_client.get("/?lang=pt")

    assert response.status_code == 200
    assert "shell-pt" in response.text
    assert "no-store" in response.headers["cache-control"]


def test_english_is_the_default_document(root_client):
    assert "shell-pt" not in root_client.get("/").text
    assert "shell-pt" not in root_client.get("/?lang=en").text


def test_portuguese_document_is_never_cached_immutable(root_client):
    """A document with a dot in its name must not be pinned immutable."""
    response = root_client.get("/index.pt.html")

    assert "shell-pt" in response.text
    assert "no-store" in response.headers["cache-control"]
    assert "immutable" not in response.headers["cache-control"]


def test_unknown_navigation_keeps_the_requested_language(root_client):
    response = root_client.get("/next/old?lang=pt", headers={"accept": "text/html"})

    assert "shell-pt" in response.text


def test_missing_portuguese_document_falls_back_to_english(tmp_path):
    app = Starlette()
    app.mount(
        "/",
        SPAStaticFiles(
            directory=str(_build_dist(tmp_path, portuguese=False)), html=True
        ),
    )
    with TestClient(app) as client:
        response = client.get("/?lang=pt")

    assert response.status_code == 200
    assert "shell-pt" not in response.text
    assert "shell" in response.text


def test_unknown_navigation_route_falls_back_to_shell(client):
    response = client.get("/next/privacy", headers={"accept": "text/html"})

    assert response.status_code == 200
    assert "shell" in response.text
    cache_control = response.headers["cache-control"]
    assert "no-store" in cache_control
    assert "immutable" not in cache_control


def test_missing_asset_file_is_404_not_shell(client):
    response = client.get("/next/assets/missing.js")

    # Regression guard: an unknown *file* must never be answered with the HTML
    # shell (nor cached as an immutable asset).
    assert response.status_code == 404
    assert "shell" not in response.text
    assert "immutable" not in response.headers.get("cache-control", "")


def test_hashed_asset_is_served_immutable(client):
    response = client.get("/next/assets/app.js")

    assert response.status_code == 200
    assert ASSET_BODY in response.text
    assert "immutable" in response.headers["cache-control"]


def test_missing_file_outside_assets_is_404(client):
    response = client.get("/next/missing.json")

    assert response.status_code == 404
    assert "shell" not in response.text
    assert "immutable" not in response.headers.get("cache-control", "")


@pytest.mark.parametrize(
    "path",
    [
        "/wp-admin/install.php",
        "/wp-admin/",
        "/.env",
        "/index.php",
    ],
)
def test_scanner_probes_are_plain_text_404_on_root_mount(root_client, path):
    response = root_client.get(path)

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/plain")
    # Scanner traffic must never be answered with (and cost) the SPA shell.
    assert "shell" not in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/.ssh/id_rsa",
        "/.git/HEAD",
        "/.svn/wc.db",
        "/actuator/heapdump",
        "/wp-json/",
        "/zzcanary-0123456789",
    ],
)
def test_scanner_canaries_are_plain_text_404_without_html_accept(root_client, path):
    response = root_client.get(path, headers={"accept": "*/*"})

    # A canary is how a scanner detects a catch-all 200. The shell fallback is
    # navigation-only, so a non-HTML client must get the same plain 404 as the
    # explicit scanner guards.
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/plain")
    assert "shell" not in response.text


@pytest.mark.parametrize(
    "path",
    ["/.ssh/id_rsa", "/.git/HEAD", "/.svn/wc.db", "/actuator/heapdump", "/wp-json/"],
)
def test_sensitive_prefixes_are_404_even_with_html_accept(root_client, path):
    response = root_client.get(path, headers={"accept": "text/html"})

    # These are never client-side routes, so even a browser-shaped request
    # must not receive the shell.
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/plain")
    assert "shell" not in response.text


def test_unknown_path_without_html_accept_is_404(root_client):
    response = root_client.get("/some/deep/link", headers={"accept": "*/*"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/plain")
    assert "shell" not in response.text


def test_missing_asset_stays_404_for_a_navigation_accept(root_client):
    response = root_client.get("/assets/missing.js", headers={"accept": "text/html"})

    # The navigation fallback must never resurrect a missing hashed asset.
    assert response.status_code == 404
    assert "shell" not in response.text


def test_websocket_upgrade_is_closed_cleanly(root_client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with root_client.websocket_connect("/_event/"):
            pass

    # No StaticFiles assertion, no 500: a stale Reflex client gets a policy
    # close (1008) instead of a traceback on every retry.
    assert exc.value.code == 1008


@pytest.mark.asyncio
async def test_non_http_non_websocket_scope_is_ignored(tmp_path):
    mount = SPAStaticFiles(directory=str(_build_dist(tmp_path)), html=True)
    sent = []

    async def receive():
        return {"type": "lifespan.startup"}

    async def send(message):
        sent.append(message)

    await mount({"type": "lifespan", "path": "/"}, receive, send)

    assert sent == []


@pytest.mark.parametrize("path", ["/_event", "/_event/", "/_upload/x"])
def test_backend_prefixes_are_plain_text_404_on_root_mount(root_client, path):
    response = root_client.get(path)

    # Regression guard: a stale Reflex client hitting /_event must get a clear
    # 404, never the SPA shell (HTML here breaks the Engine.IO handshake).
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/plain")
    assert "shell" not in response.text


def test_unknown_navigation_on_root_mount_still_serves_shell(root_client):
    response = root_client.get("/some/deep/link", headers={"accept": "text/html"})

    # The guards must not swallow the client-side router's fallback.
    assert response.status_code == 200
    assert "shell" in response.text
    cache_control = response.headers["cache-control"]
    assert "no-store" in cache_control
    assert "immutable" not in cache_control


def test_backend_prefix_404_logs_normalized_path_only(root_client, caplog):
    with caplog.at_level(logging.WARNING, logger="preconsult.observability"):
        response = root_client.get("/_event?sid=should-not-be-logged")

    assert response.status_code == 404

    records = [
        record
        for record in caplog.records
        if "static.backend_prefix_404" in record.getMessage()
    ]
    assert len(records) == 1

    message = records[0].getMessage()
    # Metadata only: the normalized path, never the query string or user input.
    assert "path='_event'" in message
    assert "?" not in message
    assert "should-not-be-logged" not in message
