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
    assert state.step_progress == 14  # int(1/7 * 100) = 14
    
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
        assert "Lighthouse/PageSpeed detected. Mocking WebSocket" in html_body
        assert "MockWebSocket" in html_body
        
        # Verify other replacements happened
        assert "https://pre-consult.org/og-image.png" in html_body
        assert "hreflang" in html_body
        assert "schema.org" in html_body
        assert "WebPage" in html_body
        assert "preload" in html_body
    finally:
        StaticFiles.get_response = original_get_response

