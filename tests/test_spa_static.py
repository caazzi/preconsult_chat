"""Caching + fallback contract of the shadow SPA static mount (``/next``).

A client-side router needs unknown *navigation* routes to fall back to
``index.html``, but a missing *file* must stay a 404: serving HTML for a missing
hashed asset — and letting it be cached ``immutable`` — is how a partial deploy
turns into "Unexpected token '<'" and a poisoned browser/CDN cache.
"""

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from reflex_app.preconsult.preconsult import SPAStaticFiles

SHELL = "<html>shell</html>"
ASSET_BODY = "console.log(1)"


@pytest.fixture()
def client(tmp_path):
    (tmp_path / "index.html").write_text(SHELL)
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text(ASSET_BODY)

    app = Starlette()
    app.mount("/next", SPAStaticFiles(directory=str(tmp_path), html=True))
    with TestClient(app) as test_client:
        yield test_client


def test_index_is_served_no_store(client):
    response = client.get("/next/")

    assert response.status_code == 200
    assert "shell" in response.text
    cache_control = response.headers["cache-control"]
    assert "no-store" in cache_control
    assert "immutable" not in cache_control


def test_unknown_navigation_route_falls_back_to_shell(client):
    response = client.get("/next/privacy")

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
