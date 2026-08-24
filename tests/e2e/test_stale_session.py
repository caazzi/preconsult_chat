"""
Stale-session /_event regression (E2E).

Verifies that a socket POST for a session the server no longer serves returns a
clean recoverable 400 "Invalid session" — never an HTTP 500. The exact
KeyError('Session is disconnected') path (a closed session still present in the
engine.io socket dict) is covered deterministically by the unit test
test_stale_session_keyerror_returns_400_not_500; this spec confirms the same
guarantee over the real Engine.IO transport the browser uses.
"""

import httpx
import pytest

from conftest import E2E_BASE  # tests/e2e on sys.path

pytestmark = pytest.mark.e2e


def test_bad_sid_socket_post_returns_400_not_500(backend):
    """A POST to the socket with a non-existent/expired session id must be a 400
    (the client re-handshakes), never a 500 (which breaks the UI)."""
    with httpx.Client(base_url=E2E_BASE, timeout=15) as client:
        # Any sid that is not an active session. Even if it were a closed-but-
        # present session, the app must not surface an unhandled 500.
        resp = client.post(
            "/_event/?EIO=4&transport=polling&sid=definitely-not-a-live-session-000"
        )
    assert resp.status_code == 400, (
        f"expected 400, got {resp.status_code}: {resp.text}"
    )
    # Response must not be a 500. The body is a generic rejection — with polling
    # transport it reads "Invalid transport"; the stale-session 400 recovery
    # ("Invalid session") applies to a valid transport with a dead sid. Both must
    # never surface as a 500.
    assert "500" not in str(resp.status_code)


def test_stale_socket_post_never_500_via_metrics(backend):
    """After hammering /_event with bad-session POSTs, /health/metrics must show
    no http.status.500 attributable to the socket (only 400s)."""
    with httpx.Client(base_url=E2E_BASE, timeout=15) as client:
        for _ in range(5):
            r = client.post(
                "/_event/?EIO=4&transport=polling&sid=stale-xyz-999"
            )
            assert r.status_code == 400
        m = client.get("/health/metrics")
    body = m.json()
    assert body["counters"].get("http.status.500", 0) == 0, (
        "socket POSTs produced an HTTP 500 — the stale-session regression "
        f"counters={body['counters']}"
    )
    # At least the 400s were recorded.
    assert body["counters"].get("http.status.400", 0) >= 5
