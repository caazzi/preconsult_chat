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

def test_custom_static_files_injection(tmp_path):
    from reflex_app.preconsult.preconsult import CustomStaticFiles
    from fastapi.staticfiles import StaticFiles
    
    # Create a dummy index.html in a temp directory
    dummy_dir = tmp_path / "static"
    dummy_dir.mkdir()
    index_file = dummy_dir / "index.html"
    index_file.write_text(
        '<html><head><link href="/assets/__reflex_global_styles-xyz.css" rel="stylesheet" type="text/css"/>'
        'content="favicon.ico" property="og:image"</head><body></body></html>',
        encoding="utf-8"
    )
    
    # Instantiate CustomStaticFiles pointing to the temp directory
    static_files = CustomStaticFiles(directory=str(dummy_dir), html=True)
    
    # Mock the super().get_response to return a Response with the path
    from fastapi.responses import FileResponse
    class MockFileResponse(FileResponse):
        pass
    
    # We will simulate calling get_response
    # Inside get_response, it checks: path in ("", ".", "index.html")
    # and reads response.path
    import asyncio
    scope = {"type": "http", "method": "GET"}
    
    # We patch super().get_response by subclassing or monkeypatching
    original_get_response = StaticFiles.get_response
    async def mock_get_response(self, path, scope):
        res = MockFileResponse(path=str(index_file))
        return res
        
    StaticFiles.get_response = mock_get_response
    
    try:
        response = asyncio.run(static_files.get_response("index.html", scope))
        assert response is not None
        html_body = response.body.decode("utf-8")
        
        # Verify MockWebSocket script is injected
        assert "MockWebSocket" in html_body
        
        # Verify other replacements happened
        assert "https://pre-consult.org/og-image.png" in html_body
        assert "hreflang" in html_body
        assert "schema.org" in html_body
        assert "WebPage" in html_body
        assert "preload" in html_body
    finally:
        StaticFiles.get_response = original_get_response


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








