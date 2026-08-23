"""
Socket-session regression & wizard-navigation E2E.

These drive a REAL browser against a REAL (single-worker) backend over the real
Engine.IO/Socket.IO path. They exist because the multi-worker regression —
`400 "Invalid session <sid>"` on /_event, surfacing as "Cannot connect to
server: xhr post error" — is only visible through a browser making sustained
polling requests; no curl probe or unit state test can reproduce it.

Run with the e2e extra + Playwright browser installed:
    scripts/run_e2e.sh
"""

import re

import pytest

from conftest import E2E_BASE  # tests/e2e is inserted on sys.path by pytest

pytestmark = pytest.mark.e2e


def _dribble_interactions(page, clicks: int = 6):
    """Force enough socket round-trips on one page to surface an intermittently
    lost Engine.IO session. Every button press emits a /_event event; with a
    fragmented session store a cluster of these reliably 400s."""
    for _ in range(clicks):
        try:
            page.get_by_text("Start Preparing", exact=True).first.click(timeout=3000)
        except Exception:  # noqa: BLE001 - a button may have moved between steps
            pass
    page.wait_for_timeout(1500)


def test_socket_session_holds_with_zero_errors(page):
    """Core regression guard: sustained interaction must never lose the socket."""
    page.goto(f"{E2E_BASE}/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1000)
    _dribble_interactions(page, clicks=8)
    page.wait_for_timeout(1000)

    socket_404 = [e for e in page.socket_errors if e["kind"] == "response"]
    assert socket_404 == [], (
        "Socket session was lost during interaction (see /_event 4xx). "
        "This is the multi-worker 'Invalid session' symptom. "
        f"observed={page.socket_errors}"
    )

    console_errors = [e for e in page.socket_errors if e["kind"] == "console"]
    assert console_errors == [], f"Browser reported a socket failure: {console_errors}"


def test_start_preparing_advances_to_step1(page):
    """'Start Preparing' must transition the wizard from the landing page to
    Patient Intake without a connection error (purely client-side state over
    the socket — needs no Redis/LLM)."""
    page.goto(f"{E2E_BASE}/", wait_until="networkidle", timeout=45000)
    page.get_by_text("Start Preparing", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(2500)

    # Step 1 (Patient Intake / demographics) should be visible.
    assert "Cannot connect to server" not in page.inner_text("body")
    assert "Patient Intake" in page.inner_text("body")
    assert "Age Bracket" in page.inner_text("body")
    assert page.socket_errors == [], (
        f"Socket failure while advancing the wizard: {page.socket_errors}"
    )


def test_language_switch_keeps_socket_alive(page):
    """Toggling EN/PT language emits socket events and must not drop the session."""
    page.goto(f"{E2E_BASE}/", wait_until="networkidle", timeout=45000)
    page.get_by_text("Start Preparing", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(1500)

    # Try switching language via the in-wizard selector if present.
    lang_btns = page.get_by_text(re.compile(r"^\s*(en|pt)\s*$", re.IGNORECASE))
    for idx, _ in enumerate(lang_btns.all()[:2]):
        try:
            page.get_by_text("en", exact=True).first.click(timeout=2000)
            page.wait_for_timeout(400)
        except Exception:  # noqa: BLE001 - selector may not be present on this step
            break

    assert page.socket_errors == [], (
        f"Language switch dropped the socket: {page.socket_errors}"
    )
