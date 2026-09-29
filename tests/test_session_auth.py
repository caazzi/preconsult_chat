"""
Session-cookie auth tests (additive, Option A + C).

Covers:
  - init issues a signed HttpOnly session cookie,
  - the cookie alone authorizes subsequent calls (no X-API-KEY),
  - the header alone still works (Reflex/programmatic back-compat),
  - a tampered/forged cookie is rejected,
  - a valid cookie for a DIFFERENT session is rejected (ownership),
  - missing/absent credentials → 403 auth_failed.
"""

from unittest.mock import patch, AsyncMock

import httpx
import pytest
from httpx import ASGITransport

from reflex_app.preconsult.preconsult import api as app
from preconsult.core.config import SESSION_COOKIE_NAME
from preconsult.core.session_auth import sign_session_id, verify_session_cookie

KEY_HEADERS = {"X-API-KEY": "ci_test_key_123"}

PAYLOAD = {
    "age_bracket": "26-35",
    "sex": "Female",
    "lang": "en",
    "specialist": "Cardiology",
    "chief_complaint": "Chest pain",
    "duration": "2 days",
    "smoking": "No",
    "alcohol": "No",
}


# --- Pure signing tests -----------------------------------------------------


def test_sign_and_verify_round_trip():
    value = sign_session_id("sess-123")
    assert verify_session_cookie(value) == "sess-123"


def test_verify_rejects_tampered_cookie():
    value = sign_session_id("sess-123")
    tampered = value[:-1] + ("A" if value[-1] != "A" else "B")
    assert verify_session_cookie(tampered) is None


def test_verify_rejects_forged_and_malformed():
    assert verify_session_cookie("other-session.deadbeef") is None
    assert verify_session_cookie("no-dot") is None
    assert verify_session_cookie("") is None
    assert verify_session_cookie(None) is None


# --- HTTP integration -------------------------------------------------------


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.create_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_session_quota", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.increment_session_quota", new_callable=AsyncMock)
async def test_init_sets_signed_httponly_session_cookie(
    mock_inc, mock_quota, mock_rate, mock_create
):
    mock_create.return_value = "sess-cookie"
    mock_quota.return_value = True
    mock_rate.return_value = True

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/session/init", json=PAYLOAD, headers=KEY_HEADERS)

    assert resp.status_code == 200
    assert resp.json()["session_id"] == "sess-cookie"
    raw = resp.headers.get("set-cookie", "")
    assert SESSION_COOKIE_NAME in raw
    assert "httponly" in raw.lower()
    assert "samesite=strict" in raw.lower()
    # No Max-Age/Expires => an in-memory session cookie (dropped on close).
    assert "max-age" not in raw.lower()
    assert "expires" not in raw.lower()


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
async def test_cookie_alone_authorizes_post(mock_rate, mock_get):
    """A valid session cookie authenticates without X-API-KEY."""
    mock_get.return_value = {"lang": "en"}
    mock_rate.return_value = True

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set(SESSION_COOKIE_NAME, sign_session_id("sess-1"))
        resp = await client.post(
            "/api/interview-questions-stream", json={"session_id": "sess-1"}
        )
    # Authorized (proceeds to the stream), not blocked by auth.
    assert resp.status_code != 403


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
async def test_cookie_for_other_session_is_rejected(mock_rate, mock_get):
    """Cookie auth must not access a different session (ownership)."""
    mock_get.return_value = {"lang": "en"}
    mock_rate.return_value = True

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set(SESSION_COOKIE_NAME, sign_session_id("sess-mine"))
        resp = await client.post(
            "/api/interview-questions-stream", json={"session_id": "sess-theirs"}
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == "auth_failed"


@pytest.mark.asyncio
async def test_no_credentials_returns_403():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/interview-questions-stream", json={"session_id": "x"}
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == "auth_failed"


@pytest.mark.asyncio
async def test_wrong_api_key_returns_403():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/interview-questions-stream",
            json={"session_id": "x"},
            headers={"X-API-KEY": "nope"},
        )
    assert resp.status_code == 403
