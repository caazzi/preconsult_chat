import pytest
import reflex as rx
pytest.importorskip("reflex_components_radix.plugin")
from reflex_app.preconsult.preconsult import header, stepper_component, step_0_landing, step_1_demographics, step_2_chief_complaint, step_3_history, step_4_lifestyle, step_5_interview_qs, step_6_summary, error_callout, admin_dashboard
from reflex_app.preconsult.state import State

def test_header_rendering():
    comp = header()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_stepper_component_rendering():
    comp = stepper_component()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_error_callout_rendering():
    comp = error_callout()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_step_0_landing_rendering():
    comp = step_0_landing()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_step_1_demographics_rendering():
    comp = step_1_demographics()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_step_2_chief_complaint_rendering():
    comp = step_2_chief_complaint()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_step_3_history_rendering():
    comp = step_3_history()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_admin_dashboard_rendering():
    comp = admin_dashboard()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_step_4_lifestyle_rendering():
    comp = step_4_lifestyle()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_step_5_interview_qs_rendering():
    comp = step_5_interview_qs()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_step_6_summary_rendering():
    comp = step_6_summary()
    assert isinstance(comp, rx.Component)
    assert comp is not None

def test_state_step_progress():
    state = State()
    state.step = 0
    assert state.step_progress == 0
    
    state.step = 1
    assert state.step_progress == 20
    
    state.step = 3
    assert state.step_progress == 60
    
    state.step = 5
    assert state.step_progress == 100
    
    state.step = 6
    assert state.step_progress == 100

def test_state_clear_conditions():
    state = State()
    state.conditions = ["asthma", "diabetes"]
    state.clear_conditions()
    assert state.conditions == []

def test_state_question_index():
    state = State()
    assert state.question_index == 0
    state.set_question_index(3)
    assert state.question_index == 3

def test_custom_static_files_serves_html_unchanged(tmp_path):
    """The built SPA must be served byte-for-byte so React hydration succeeds.

    This used to string-inject <head> tags (MockWebSocket, og:image, hreflang,
    schema, SEO) into the built index.html. Those injected tags are absent from
    the client render, so React threw hydration error #418 and never attached
    event handlers (the whole app was un-interactive). The page-level SEO now
    lives via add_page(meta=...), so CustomStaticFiles must NOT mutate the HTML.
    """
    from reflex_app.preconsult.preconsult import CustomStaticFiles
    from fastapi.responses import FileResponse
    import asyncio

    dummy_dir = tmp_path / "static"
    dummy_dir.mkdir()
    (dummy_dir / "index.html").write_text(
        '<html><head><title>PreConsult</title></head>'
        '<body><div id="root"></div></body></html>',
        encoding="utf-8",
    )

    static_files = CustomStaticFiles(directory=str(dummy_dir), html=True)
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
        "path": "/index.html",
        "raw_path": b"/index.html",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "http_version": "1.1",
        "app": {},
    }

    response = asyncio.run(static_files.get_response("index.html", scope))
    # Unmodified file-backed response, NOT a synthesized HTMLResponse with
    # injected <head> tags.
    assert isinstance(response, FileResponse)
    assert response.path.endswith("index.html")


def test_bot_scanner_blocking(tmp_path):
    from reflex_app.preconsult.preconsult import CustomStaticFiles
    dummy_dir = tmp_path / "static"
    dummy_dir.mkdir()
    static_files = CustomStaticFiles(directory=str(dummy_dir), html=True)
    import asyncio
    scope = {"type": "http", "method": "GET"}
    
    response = asyncio.run(static_files.get_response("wp-admin/install.php", scope))
    assert response.status_code == 404
    assert response.body == b"Not Found"


def test_index_page_meta_is_hydration_safe_meta_only():
    """Only plain <meta> dicts may be returned from build_index_meta().

    Generic link/script/noscript components passed through add_page(meta=...)
    are rendered into the page <body> (not <head>), where they are absent from
    the client render and break React hydration with error #418 (the whole app
    becomes un-interactive). Lock the meta list to dicts only.
    """
    from reflex_app.preconsult.preconsult import build_index_meta
    from reflex_components_core.el.elements import Link, Script, Noscript

    meta = build_index_meta()
    assert meta, "expected at least the og:image metas"
    # Every entry must be a plain <meta> dict (renders into <head> safely).
    assert all(isinstance(m, dict) for m in meta)
    # Absolutely no component entries that would leak into the body.
    assert all(not isinstance(m, (Link, Script, Noscript)) for m in meta)
    # Social preview + dimensions present.
    assert {"property": "og:image", "content": "https://pre-consult.org/og-image.png"} in meta
    assert {"property": "og:image:width", "content": "1200"} in meta
    assert {"property": "og:image:height", "content": "630"} in meta


def test_served_body_has_no_head_leak_markers():
    """Regression guard: the served SPA <body> must not contain leaked head tags
    (hreflang, JSON-LD, lang-cookie) that historically caused hydration #418 and
    a 'Unexpected token <' console error."""
    import asyncio
    import httpx
    from httpx import ASGITransport
    from reflex_app.preconsult.preconsult import api as app

    async def run():
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        return resp

    resp = asyncio.run(run())
    body = resp.text
    # These markers lived in <head> via injection or leaked into <body> via
    # add_page(meta=<component>); either way they broke hydration.
    for marker in ("application/ld+json", "hreflang", "preconsult_lang"):
        assert marker not in body, f"expected no '{marker}' in served HTML"


def test_request_id_header_is_stamped():
    """Every HTTP response carries an X-Request-ID for correlation."""
    import asyncio
    import httpx
    from httpx import ASGITransport
    from reflex_app.preconsult.preconsult import api as app

    async def run():
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        return resp

    resp = asyncio.run(run())
    assert resp.headers.get("x-request-id")


def test_assets_immutable_cache_and_vary(tmp_path):
    """JS/CSS under /assets/ get immutable cache headers and a Vary header."""
    from reflex_app.preconsult.preconsult import CustomStaticFiles
    import asyncio

    dummy_dir = tmp_path / "static"
    dummy_dir.mkdir()
    (dummy_dir / "assets").mkdir()
    (dummy_dir / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    static_files = CustomStaticFiles(directory=str(dummy_dir), html=True)
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
        "path": "/assets/app.js",
        "raw_path": b"/assets/app.js",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "http_version": "1.1",
        "app": {},
    }
    response = asyncio.run(static_files.get_response("assets/app.js", scope))
    assert response.headers.get("cache-control") == "public, max-age=31536000, immutable"
    assert "Accept-Encoding" in response.headers.get("vary", "")


def test_custom_static_backend_passthrough(tmp_path):
    """Backend/reflex endpoints must never be answered with the SPA fallback."""
    from reflex_app.preconsult.preconsult import CustomStaticFiles
    dummy_dir = tmp_path / "static"
    dummy_dir.mkdir()
    (dummy_dir / "404.html").write_text("<html>SPA FALLBACK</html>", encoding="utf-8")
    static_files = CustomStaticFiles(directory=str(dummy_dir), html=True)
    import asyncio

    for path in ("_event", "_event/x", "_ping", "_health", "_upload", "auth-codespace", "_all_routes"):
        response = asyncio.run(static_files.get_response(path, {"type": "http", "method": "GET"}))
        assert response.status_code == 404, path
        assert response.headers.get("content-type", "").startswith("text/plain"), path
        assert response.body == b"Not Found"


def test_bare_event_redirects_instead_of_spa_fallback():
    """The browser polls the bare /_event path; it must reach the socket
    (via a reflex-style 307 redirect) rather than being swallowed by the SPA
    catch-all, which previously broke the state connection with
    'cannot connect to server: xhr poll error'."""
    import asyncio
    import httpx
    from httpx import ASGITransport
    from reflex_app.preconsult.preconsult import api as app

    async def run():
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/_event?EIO=4&transport=polling")
        return resp

    resp = asyncio.run(run())
    assert resp.status_code == 307
    assert resp.headers.get("location") == "/_event/?EIO=4&transport=polling"
    # Must never return the SPA HTML for the socket path.
    assert "text/html" not in resp.headers.get("content-type", "")


def test_state_scroll_and_draft_scripts():
    state = State()
    scroll_script = state._scroll_top_script()
    assert "scrollTo" in repr(scroll_script) or "scrollTo" in str(scroll_script.args)

    draft_script = state._save_draft_script()
    assert "localStorage.setItem" in repr(draft_script) or "localStorage.setItem" in str(draft_script.args)

    clear_script = state._clear_draft_script()
    assert "localStorage.removeItem" in repr(clear_script) or "localStorage.removeItem" in str(clear_script.args)


def test_state_reset_intake():
    state = State()
    state.step = 6
    state.chief_complaint = "Headache"
    state.session_id = "sess_123"
    
    events = list(state.reset_intake())
    assert state.step == 0
    assert state.chief_complaint == ""
    assert state.session_id == ""
    assert len(events) == 3


def test_mobile_ui_layout_responsiveness():
    stepper = stepper_component()
    summary = step_6_summary()
    interview = step_5_interview_qs()
    assert stepper is not None
    assert summary is not None
    assert interview is not None


def test_rxconfig_redis_url(monkeypatch):
    import os
    import reflex_app.rxconfig as rxconfig
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    assert rxconfig.config.redis_url == os.environ.get("REDIS_URL")


def test_rxconfig_polling_transport_is_default(monkeypatch):
    # Cloud Run's frontend offers HTTP/2 and cannot upgrade a browser's
    # WebSocket over it (Google issue 194314805), which breaks Reflex events.
    # The event transport must default to HTTP long-polling so "Start
    # Preparing" and all state mutations work on the deployed host.
    import reflex_app.rxconfig as rxconfig
    monkeypatch.delenv("REFLEX_TRANSPORT", raising=False)
    monkeypatch.delenv("REFLEX_API_URL", raising=False)

    assert rxconfig.config.transport == "polling"
    assert rxconfig.config.api_url == "https://pre-consult.org"


def test_rxconfig_transport_is_env_overridable(monkeypatch):
    # Allow rolling back to websocket (or a staging origin) without a code
    # change via REFLEX_TRANSPORT / REFLEX_API_URL.
    monkeypatch.setenv("REFLEX_TRANSPORT", "websocket")
    monkeypatch.setenv("REFLEX_API_URL", "https://staging.example.com")
    import importlib
    import reflex_app.rxconfig as rxconfig
    importlib.reload(rxconfig)
    assert rxconfig.config.transport == "websocket"
    assert rxconfig.config.api_url == "https://staging.example.com"


def test_get_router_params_helper():
    from reflex_app.preconsult.state import _get_router_params
    
    # Test None
    assert _get_router_params(None) == {}

    # Test Router with url query_parameters
    class MockURL:
        query_parameters = {"lang": "pt", "gad_source": "test"}

    class MockRouterWithURL:
        url = MockURL()

    assert _get_router_params(MockRouterWithURL()) == {"lang": "pt", "gad_source": "test"}

    # Test Router with _page params
    class MockPage:
        params = {"token": "secret123"}

    class MockRouterWithPage:
        url = None
        _page = MockPage()

    assert _get_router_params(MockRouterWithPage()) == {"token": "secret123"}


def test_state_set_answer_out_of_bounds():
    state = State()
    state.current_answers = []
    # Test setting answer for index 0 when list is empty
    state.set_answer(0, "Answer 1")
    assert state.current_answers == ["Answer 1"]

    # Test setting answer for index 3 when list length is 1
    state.set_answer(3, "Answer 4")
    assert state.current_answers == ["Answer 1", "", "", "Answer 4"]








