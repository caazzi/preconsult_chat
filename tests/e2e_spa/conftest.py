"""
E2E fixtures for the shadow SPA (web/) served at /next.

Reuses the same real-backend approach as tests/e2e: one gunicorn worker serving
both the Reflex app (/) and the SPA (/next) plus /api. The SPA talks only to
/api over plain HTTP with the session cookie, so these specs exercise that path
hermetically — no live Bedrock/Redis. API endpoints the SPA calls are
intercepted at the browser route layer so no real session/LLM/Redis is needed.

Kept OUT of the coverage-gated unit suite (see pyproject norecursedirs / marker).
"""

import os
import signal
import subprocess
import time
import urllib.request

import pytest

E2E_HOST = os.environ.get("E2E_HOST", "127.0.0.1")
E2E_PORT = int(os.environ.get("E2E_PORT", "8000"))
E2E_BASE = f"http://{E2E_HOST}:{E2E_PORT}"
E2E_WORKERS = os.environ.get("E2E_WORKERS", "1")
_APP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reflex_app")
_WEB_DIST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist")
)


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
    if not os.path.exists(os.path.join(_WEB_DIST, "index.html")):
        pytest.skip(
            f"web/dist not built at {_WEB_DIST}; run `npm run build` in web/ first"
        )
    proc = None
    try:
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
        env["SESSION_SECRET"] = env.get("SESSION_SECRET", "e2e-session-secret")
        env["SESSION_COOKIE_SECURE"] = "false"
        env["WEB_DIST_DIR"] = _WEB_DIST
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
def page(browser, backend):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
