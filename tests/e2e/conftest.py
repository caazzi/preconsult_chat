"""
E2E fixtures: boot the real PreConsult backend (single gunicorn worker) and
provide a Playwright browser.

The landing→Step-1 wizard transition and the socket-session stability are purely
client-side state over the Socket.IO channel, so the current specs need no live
Vertex AI or serverless Redis. Should deeper steps (session init, LLM streams)
be added later, intercept their API via `page.route` in the spec rather than
touching real Vertex/Redis.

These specs are intentionally NOT part of the coverage-gated unit suite: they
exercise the real HTTP + Socket.IO path (the exact surface where the multi-worker
"Invalid session" regression appeared) rather than the Python state machine.
"""

import os
import signal
import subprocess
import time
import urllib.request

import pytest

# Backend under test. Must match the frontend origin the client was built for
# (see scripts/run_e2e.sh: it runs `reflex export` with REFLEX_API_URL set to
# this). 127.0.0.1 so nothing is exposed beyond the test host.
E2E_HOST = os.environ.get("E2E_HOST", "127.0.0.1")
E2E_PORT = int(os.environ.get("E2E_PORT", "8000"))
E2E_BASE = f"http://{E2E_HOST}:{E2E_PORT}"
E2E_WORKERS = os.environ.get("E2E_WORKERS", "1")
_APP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reflex_app")


def _wait_for_http(url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return
        except Exception as e:  # noqa: BLE001 - retry until deadline
            last = e
        time.sleep(0.5)
    raise RuntimeError(f"Backend at {url} not healthy in {timeout}s: {last}")


@pytest.fixture(scope="session")
def backend() -> str:
    """Boot the real app under gunicorn with a single worker.

    Single worker mirrors the production fix (`--workers 1`): Reflex's
    Engine.IO session store is in-memory per worker, so more workers split one
    browser's polling across disjoint sessions and produce
    `400 "Invalid session"`. Override via E2E_WORKERS to reproduce the bug.
    """
    proc = None
    try:
        # Locate gunicorn in the repo venv (not necessarily on PATH). cwd must be
        # reflex_app so the static mount (.web/build/client) and served index.html
        # are found.
        gunicorn = os.environ.get("E2E_GUNICORN")
        if not gunicorn:
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            candidate = os.path.join(project_root, ".venv", "bin", "gunicorn")
            gunicorn = candidate if os.path.exists(candidate) else "gunicorn"
        cmd = [
            gunicorn,
            "preconsult.preconsult:api",
            "--bind",
            f"{E2E_HOST}:{E2E_PORT}",
            "--worker-class",
            "uvicorn.workers.UvicornWorker",
            "--workers",
            E2E_WORKERS,
            "--threads",
            "4",
        ]
        env = dict(os.environ)
        env["PRECONSULT_API_KEY"] = env.get("PRECONSULT_API_KEY", "e2e_test_key")
        env.pop("REDIS_URL", None)
        proc = subprocess.Popen(
            cmd,
            cwd=_APP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
        )
        _wait_for_http(f"{E2E_BASE}/health/live")
        yield E2E_BASE
    finally:
        if proc:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, backend, request):
    """A fresh page for each test, collecting any /_event failures onto
    ``page.socket_errors`` so the socket-session regression is assertable."""
    context = browser.new_context()
    page = context.new_page()
    errors: list[dict] = []
    page.socket_errors = errors

    def on_response(resp):
        try:
            if "/_event" in resp.url and resp.status >= 400:
                errors.append({"url": resp.url, "status": resp.status, "kind": "response"})
        except Exception:  # noqa: BLE001 - diagnostics must never break the test
            pass

    def on_console(msg):
        text = (msg.text or "").lower()
        if any(
            k in text
            for k in (
                "unsupported version",
                "cannot connect to server",
                "invalid session",
                "xhr post error",
                "xhr poll error",
            )
        ):
            errors.append({"message": (msg.text or "")[:200], "kind": "console"})

    page.on("response", on_response)
    page.on("console", on_console)

    yield page

    if request.node.rep_call.failed:
        try:
            os.makedirs("test-results", exist_ok=True)
            page.screenshot(path=os.path.join("test-results", f"{request.node.name}.png"))
        except Exception:  # noqa: BLE001 - optional artifact
            pass
    context.close()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    # Store rep_call so the page fixture can screenshot on failure.
    if call.when == "call":
        item.rep_call = call
