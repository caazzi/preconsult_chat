"""HTTP edge contracts for the mounted API app.

Three cross-cutting behaviours are locked here:

* the bot gate answers blocked CLI user-agents on Redis-backed paths with a
  machine-readable JSON 403 (``bot_blocked``) without touching storage, while
  leaving real browsers to the normal auth path (``auth_failed``);
* request-body validation failures return the stable ``validation_failed`` 422
  with sanitized ``errors`` (no ``input``/``ctx``, no submitted values);
* a patient-supplied value (the PHI canary) is never echoed in the response nor
  written to the logs on that rejection path.
"""

import logging

import httpx
import pytest
from httpx import ASGITransport

from reflex_app.preconsult.preconsult import api as app

BASE_URL = "http://test"
AUTH_HEADERS = {"X-API-KEY": "ci_test_key_123"}
BOT_UA = "curl/8.5.0"
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PHI_CANARY = "ZZ-PHI-CANARY-1234"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL)


# ---------------------------------------------------------------------------
# Bot gate: JSON 403 for scanners, untouched auth path for browsers.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bot_gate_blocks_cli_user_agent_on_redis_path():
    async with _client() as client:
        response = await client.post(
            "/api/session/init",
            headers={"User-Agent": BOT_UA},
            json={},
        )

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["code"] == "bot_blocked"
    assert body["detail"] == "Forbidden"


@pytest.mark.asyncio
async def test_bot_gate_allows_browser_user_agent_through_to_auth():
    async with _client() as client:
        response = await client.post(
            "/api/session/init",
            headers={"User-Agent": BROWSER_UA},
            json={},
        )

    # No credentials supplied: the browser is NOT bot-blocked, it reaches the
    # auth dependency and gets the normal auth_failed contract.
    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "auth_failed"
    assert body.get("code") != "bot_blocked"


# ---------------------------------------------------------------------------
# 422 request-validation contract (sanitized, machine-readable).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_validation_returns_sanitized_422():
    async with _client() as client:
        response = await client.post(
            "/api/session/init",
            headers=AUTH_HEADERS,
            json={"conditions": "not_a_list"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_failed"
    assert isinstance(body["detail"], str)
    assert body["errors"]
    for error in body["errors"]:
        assert "input" not in error
        assert "ctx" not in error


@pytest.mark.asyncio
async def test_phi_canary_never_echoed_or_logged(caplog):
    payload = {"chief_complaint": PHI_CANARY, "conditions": "not_a_list"}

    with caplog.at_level(logging.WARNING):
        async with _client() as client:
            response = await client.post(
                "/api/session/init",
                headers=AUTH_HEADERS,
                json=payload,
            )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
    # The submitted value must not survive anywhere in the rejection path.
    assert PHI_CANARY not in response.text
    assert PHI_CANARY not in caplog.text


@pytest.mark.asyncio
async def test_generate_pdf_validation_runs_before_session_lookup():
    async with _client() as client:
        response = await client.post(
            "/api/generate-pdf",
            headers=AUTH_HEADERS,
            json={"session_id": "x", "qa_pairs": []},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_failed"
    for error in body["errors"]:
        assert "input" not in error
        assert "ctx" not in error
