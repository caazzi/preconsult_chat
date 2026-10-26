"""
Authz-matrix enforcement tests.

Each `/api/*` route must require authentication. A request with no credential
must be rejected with the stable `auth_failed` code BEFORE any handler work.
This pins the matrix in docs/authz-matrix.md so a new route cannot ship
unauthenticated. `POST /api/session/init` is the session bootstrap: it is
asserted here under the default `ALLOW_PUBLIC_INIT=false`, and its open mode
is covered by tests/test_public_init.py.
"""

import httpx
import pytest
from httpx import ASGITransport

from reflex_app.preconsult.preconsult import api as app

# (method, path, json-body-or-None)
API_ROUTES = [
    ("POST", "/api/session/init", {}),
    ("POST", "/api/initial-questions-stream", {"session_id": "x", "chief_complaint": "pain"}),
    ("POST", "/api/interview-questions-stream", {"session_id": "x"}),
    ("POST", "/api/generate-pdf", {"session_id": "x", "qa_pairs": [{"question": "?", "answer": "a"}]}),
    ("POST", "/api/analytics/event", {"event": "intake_started"}),
    ("GET", "/api/analytics/stats", None),
]


def _id(route):
    method, path, _ = route
    return f"{method} {path}"


@pytest.mark.asyncio
@pytest.mark.parametrize("route", API_ROUTES, ids=_id)
async def test_api_route_requires_auth(route):
    method, path, body = route
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if method == "GET":
            resp = await client.get(path)
        else:
            resp = await client.post(path, json=body or {})
    assert resp.status_code == 403, f"{_id(route)} is not auth-protected"
    assert resp.json()["code"] == "auth_failed"
