"""Public session bootstrap contract (ALLOW_PUBLIC_INIT).

The React SPA (served at /) has no credential before it calls
`POST /api/session/init`, and that endpoint is what issues the cookie. So the
bootstrap must be callable anonymously *without* weakening any other route.

Default stays false: the bootstrap is only opened when the flag is set, because
its per-IP quota is the cost control for a login-less product. These tests pin
both sides of the flag plus the payload bounds that make opening it safe.
"""

import httpx
import pytest
from httpx import ASGITransport

import preconsult.api.endpoints as endpoints
import preconsult.services.session_service as srv
from preconsult.core.config import SESSION_COOKIE_NAME
from preconsult.host import app
from tests.fakes import session_payload

PAYLOAD = session_payload(
    duration="A few days",
    smoking="Never",
    alcohol="Never",
)

PDF_BODY = {"session_id": "", "qa_pairs": [{"question": "Fever?", "answer": "No"}]}


@pytest.fixture
async def memory_store(monkeypatch):
    """Force the in-memory session/limiter store so no Redis is needed."""
    monkeypatch.setattr(srv, "_redis_available", False)
    await srv._memory_limiter.clear()
    yield


@pytest.fixture
def public_init(memory_store, monkeypatch):
    monkeypatch.setattr(endpoints, "ALLOW_PUBLIC_INIT", True)


@pytest.fixture
def closed_init(memory_store, monkeypatch):
    monkeypatch.setattr(endpoints, "ALLOW_PUBLIC_INIT", False)


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Flag semantics
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_init_requires_a_credential_by_default(closed_init):
    async with _client() as client:
        resp = await client.post("/api/session/init", json=PAYLOAD)

    assert resp.status_code == 403
    assert resp.json()["code"] == "auth_failed"


@pytest.mark.asyncio
async def test_public_init_issues_a_session_cookie(public_init):
    async with _client() as client:
        resp = await client.post("/api/session/init", json=PAYLOAD)

    assert resp.status_code == 200, resp.text
    assert resp.json()["session_id"]

    set_cookie = resp.headers["set-cookie"]
    assert set_cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie.replace("samesite", "SameSite")


@pytest.mark.asyncio
async def test_cookie_alone_authorizes_the_next_call(public_init):
    """The whole point of the bootstrap: no X-API-KEY after init."""
    async with _client() as client:
        init = await client.post("/api/session/init", json=PAYLOAD)
        session_id = init.json()["session_id"]

        # httpx persists Set-Cookie on the client; no header is sent here.
        resp = await client.post(
            "/api/generate-pdf",
            json={**PDF_BODY, "session_id": session_id},
        )

    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_cookie_cannot_touch_another_session(public_init):
    async with _client() as client:
        first = await client.post("/api/session/init", json=PAYLOAD)
        other = await client.post("/api/session/init", json=PAYLOAD)

    other_id = other.json()["session_id"]
    assert first.json()["session_id"] != other_id

    # Cookie jar still belongs to the first session; ask for the second one.
    async with _client() as client:
        client.cookies.set(
            SESSION_COOKIE_NAME,
            first.headers["set-cookie"].split(";")[0].split("=", 1)[1],
        )
        resp = await client.post(
            "/api/generate-pdf",
            json={**PDF_BODY, "session_id": other_id},
        )

    assert resp.status_code == 403
    assert resp.json()["code"] == "auth_failed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        (
            "POST",
            "/api/generate-pdf",
            {"session_id": "x", "qa_pairs": [{"question": "?", "answer": "a"}]},
        ),
        (
            "POST",
            "/api/initial-questions-stream",
            {"session_id": "x", "chief_complaint": "pain"},
        ),
        ("POST", "/api/interview-questions-stream", {"session_id": "x"}),
        ("POST", "/api/analytics/event", {"event": "intake_started"}),
        ("GET", "/api/analytics/stats", None),
    ],
)
async def test_public_init_does_not_open_other_routes(public_init, method, path, body):
    async with _client() as client:
        resp = await client.request(method, path, json=body)

    assert resp.status_code == 403
    assert resp.json()["code"] == "auth_failed"


# ---------------------------------------------------------------------------
# Payload bounds (the reason opening the bootstrap is safe)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_oversized_free_text_is_rejected(public_init):
    async with _client() as client:
        resp = await client.post(
            "/api/session/init",
            json={**PAYLOAD, "chief_complaint": "x" * 2001},
        )

    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_failed"


@pytest.mark.asyncio
async def test_too_many_list_entries_are_rejected(public_init):
    async with _client() as client:
        resp = await client.post(
            "/api/session/init",
            json={**PAYLOAD, "conditions": ["asthma"] * 21},
        )

    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_failed"


@pytest.mark.asyncio
async def test_oversized_list_entry_is_rejected(public_init):
    async with _client() as client:
        resp = await client.post(
            "/api/session/init",
            json={**PAYLOAD, "medications": ["y" * 101]},
        )

    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_failed"
