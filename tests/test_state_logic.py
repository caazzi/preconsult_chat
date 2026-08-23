"""
Behavioral tests for the Reflex client state logic
(reflex_app/preconsult/state.py).

These cover the highest-regression-risk code in the app: the multi-step intake
wizard orchestration, session-init payload construction, SSE question-stream
parsing (including the emergency red-flag path) and the PDF download flow.

Testing notes:
- ``State`` may be instantiated directly under the pytest test environment.
- A background ``@rx.event(background=True)`` handler stores the raw coroutine
  body in ``EventHandler.fn``; calling ``.fn(state)`` runs it inline on the
  running event loop. This avoids reflex's fire-and-forget background scheduler.
- ``init_session`` chains into ``get_interview_questions`` (another background
  handler). Reflex forbids awaiting a chained background task
  (``_no_chain_background_task_co``), so ``init_session.fn`` cannot be invoked
  directly. Instead, its pure payload-construction logic is factored into
  ``build_session_init_payload`` and tested here; the stream-parsing handler is
  tested directly.
"""

import asyncio
import json

import pytest
import reflex as rx  # noqa: F401  # required to register reflex components
import httpx

pytest.importorskip("reflex_components_radix.plugin")

from unittest.mock import patch, AsyncMock, MagicMock

from reflex_app.preconsult.state import State, AdminState, _get_router_params
from reflex_app.preconsult.state import build_session_init_payload


def sse(payload: str) -> str:
    """Render a payload exactly as the backend SSE endpoint emits it:
    ``data: <json.dumps(payload)>\\n\\n`` as a single logical line."""
    return f"data: {json.dumps(payload)}\n\n"


class _AsyncContextManager:
    """Minimal async context manager adapter for mock responses."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


class _FakeStreamResponse:
    """Look-and-feel of an httpx streaming response for the SSE consumer.

    Only ``aiter_lines()`` is used by ``state.py``; it yields the response body
    split on real newlines, exactly like httpx.
    """

    def __init__(self, resp):
        self._resp = resp

    async def aiter_lines(self):
        text = self._resp.text
        for line in text.split("\n"):
            yield line


def routed_client(routes):
    """Build a mock ``httpx.AsyncClient`` that dispatches on the path suffix.

    This intentionally does NOT construct a real ``httpx.AsyncClient`` /
    ``MockTransport`` — those proved environment-sensitive across Python/httpx
    versions in CI. The production code only needs ``stream()`` (SSE) and
    ``post()`` (PDF), returning lightweight fakes.

    ``routes`` maps a URL suffix to a callable ``fn(url)`` returning either an
    ``httpx.Response`` or raising (to simulate a failure). Suffix matching keeps
    the tests correct regardless of ``API_BASE_URL`` causing ``/api/api/...``.
    """
    client = MagicMock(name="httpx.AsyncClient")
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    def _route(url):
        url = url if isinstance(url, str) else str(url)
        for suffix, fn in routes.items():
            if url.endswith(suffix):
                return fn
        return None

    def _stream(method, url, **kwargs):
        fn = _route(url)
        if fn is None:
            return _AsyncContextManager(_FakeStreamResponse(httpx.Response(404, text="")))
        return _AsyncContextManager(_FakeStreamResponse(fn(url)))

    async def _post(url, **kwargs):
        fn = _route(url)
        if fn is None:
            return httpx.Response(404, text="not found")
        return fn(url)

    client.stream = _stream
    client.post = _post
    return client


def _localize_en(category, key):
    # use the real State.get_localized_value against an EN state
    s = State()
    s.set_lang("en")
    return s.get_localized_value(category, key)


# ---------------------------------------------------------------------------
# Pure form state, setters and toggles
# ---------------------------------------------------------------------------

def test_initial_state_defaults():
    s = State()
    assert s.step == 0
    assert s.lang == "en"
    assert s.questions == []
    assert s.current_answers == []
    assert s.is_emergency is False
    assert s.allergies_flag is False


def test_setters_and_toggle_conditions():
    s = State()
    s.set_lang("pt")
    assert s.lang == "pt"
    s.set_lang("xx")  # invalid -> ignored
    assert s.lang == "pt"

    s.toggle_condition("asthma")
    s.toggle_condition("diabetes")
    assert sorted(s.conditions) == ["asthma", "diabetes"]
    s.toggle_condition("asthma")  # toggle off
    assert s.conditions == ["diabetes"]
    s.clear_conditions()
    assert s.conditions == []


@pytest.mark.asyncio
async def test_analytics_only_fired_after_session_exists():
    """Analytics events must not reach the Redis write path until a real
    session exists, so bots that never start the flow can't burn quota."""
    from unittest.mock import patch

    with patch("reflex_app.preconsult.state.log_analytics_event", new_callable=AsyncMock) as mock_api:
        s = State()
        # No session_id yet -> event is dropped before the HTTP/REDIS call.
        s.log_analytics_event("intake_started")
        assert mock_api.await_count == 0

        # With a real session_id the event is fanned out (create_task on the loop).
        s.session_id = "sess-abc"
        s.log_analytics_event("summary_generated")
        # Allow the background task to be scheduled/awaited.
        await asyncio.sleep(0.05)
        assert mock_api.await_count >= 1
        s.session_id = ""

def test_toggle_family_history():
    s = State()
    s.toggle_family_history("cancer")
    s.toggle_family_history("heart")
    assert sorted(s.family_history) == ["cancer", "heart"]
    s.toggle_family_history("cancer")
    assert s.family_history == ["heart"]


def test_medication_add_update_remove():
    s = State()
    s.add_medication()
    assert s.medications == [""]
    s.update_medication(0, "Losartan")
    assert s.medications == ["Losartan"]
    s.add_medication()
    assert s.medications == ["Losartan", ""]
    s.remove_medication(0)
    assert s.medications == [""]


def test_set_answer_grows_list():
    s = State()
    s.current_answers = []
    s.set_answer(0, "a")
    assert s.current_answers == ["a"]
    s.set_answer(3, "d")  # index beyond current length grows with empties
    assert s.current_answers == ["a", "", "", "d"]


def test_allergies_flag():
    s = State()
    s.set_allergies_flag(True)
    assert s.allergies_flag is True
    s.set_allergies_text("penicillin")
    assert s.allergies_text == "penicillin"
    s.set_allergies_flag(False)
    assert s.allergies_flag is False


def test_get_localized_value_maps_and_falls_back():
    s = State()
    s.set_lang("en")
    assert s.get_localized_value("duration", "today") == "Started today"
    assert s.get_localized_value("duration", "") == ""
    # unknown category / key falls back to the key itself
    assert s.get_localized_value("nope", "x") == "x"
    assert s.get_localized_value("conditions", "not-a-known-key") == "not-a-known-key"
    s.set_lang("pt")
    assert s.get_localized_value("smoking", "never") != ""


# ---------------------------------------------------------------------------
# build_session_init_payload (extracted from init_session)
# ---------------------------------------------------------------------------

def test_payload_maps_and_localizes_fields():
    payload = build_session_init_payload(
        age_bracket="26-35",
        sex="Female",
        lang="en",
        specialist="Cardiology",
        chief_complaint="Chest pain",
        complaint_detail="At night",
        conditions=["asthma"],
        medications=["Losartan", "  "],  # blank entry filtered out
        allergies_flag=True,
        allergies_text="penicillin",
        family_history=["cancer"],
        smoking="never",
        alcohol="rarely",
        duration="days",
        localize=_localize_en,
    )
    assert payload["sex"] == "Female"
    assert payload["lang"] == "en"
    assert payload["conditions"] == ["Asthma/Bronchitis"]
    assert payload["medications"] == ["Losartan"]
    assert payload["allergies"] == "penicillin"
    # duration is localized
    assert payload["duration"] != "days"


def test_payload_allergies_none_reported_when_flag_false():
    payload = build_session_init_payload(
        age_bracket="18-25",
        sex="Male",
        lang="en",
        specialist="",
        chief_complaint="",
        complaint_detail="",
        conditions=[],
        medications=[],
        allergies_flag=False,
        allergies_text="would be ignored",
        family_history=[],
        smoking="",
        alcohol="",
        duration="",
        localize=_localize_en,
    )
    assert payload["allergies"] == "None"


def test_payload_filters_all_blank_medications():
    payload = build_session_init_payload(
        age_bracket="",
        sex="",
        lang="en",
        specialist="",
        chief_complaint="",
        complaint_detail="",
        conditions=[],
        medications=["", "", "  "],
        allergies_flag=False,
        allergies_text="",
        family_history=[],
        smoking="",
        alcohol="",
        duration="",
        localize=_localize_en,
    )
    assert payload["medications"] == []


def test_payload_empty_lists_default():
    payload = build_session_init_payload(
        age_bracket="",
        sex="",
        lang="pt",
        specialist="",
        chief_complaint="",
        complaint_detail="",
        conditions=[],
        medications=[],
        allergies_flag=False,
        allergies_text="",
        family_history=[],
        smoking="",
        alcohol="",
        duration="",
        localize=_localize_en,
    )
    assert payload["conditions"] == []
    assert payload["family_history"] == []
    assert payload["lang"] == "pt"


# ---------------------------------------------------------------------------
# Step wizard transitions & validation
# ---------------------------------------------------------------------------

def test_step_progress_bounds():
    s = State()
    s.step = 0
    assert s.step_progress == 0
    s.step = 1
    assert s.step_progress == 20
    s.step = 5
    assert s.step_progress == 100
    s.step = 6  # completed
    assert s.step_progress == 100


def test_active_step_number_and_index():
    s = State()
    s.step = 0
    assert s.active_step_index == 0
    assert s.active_step_number == 1
    s.step = 3
    assert s.active_step_index == 2
    assert s.active_step_number == 3
    s.step = 7  # beyond range clamps
    assert s.active_step_index == 4
    assert s.active_step_number == 5


def test_start_intake():
    s = State()
    events = list(s.start_intake())
    assert s.step == 1
    assert len(events) == 1


def test_go_back_clamps_at_zero():
    s = State()
    list(s.go_back())  # step already 0
    assert s.step == 0
    s.step = 4
    list(s.go_back())
    assert s.step == 3


def test_go_to_step_2_requires_gender():
    s = State()
    s.set_gender("")
    events = list(s.go_to_step_2())
    assert s.step == 0
    assert s.error_message == s._t["err_gender"]
    assert len(events) == 0  # validation failure yields no actions


def test_go_to_step_2_success():
    s = State()
    s.set_gender("Female")
    events = list(s.go_to_step_2())
    assert s.step == 2
    assert s.error_message == ""
    assert len(events) == 2  # scroll + save-draft


def test_go_to_step_3_requires_specialist_and_complaint():
    s = State()
    s.set_specialist("")
    s.set_chief_complaint("")
    list(s.go_to_step_3())
    assert s.step == 0
    assert s.error_message == s._t["err_chief_complaint"]


def test_go_to_step_3_success():
    s = State()
    s.set_specialist("Cardiology")
    s.set_chief_complaint("Chest pain")
    list(s.go_to_step_3())
    assert s.step == 3


def test_go_to_step_4_and_5():
    s = State()
    list(s.go_to_step_4())
    assert s.step == 4
    list(s.go_to_step_5())
    assert s.step == 5


# ---------------------------------------------------------------------------
# detect_lang
# ---------------------------------------------------------------------------

class _FakeRouter:
    def __init__(self, query=None, headers=None):
        self.url = type("U", (), {"query_parameters": query or {}})()
        self.headers = headers or {}
        self.page = type("P", (), {"params": query or {}})()


def test_detect_lang_from_query_param():
    s = State()
    s.lang = "en"
    object.__setattr__(s, "router", _FakeRouter(query={"lang": "pt", "utm_source": "gads"}))
    s.detect_lang()
    assert s.lang == "pt"
    assert s.utm_source == "gads"


def test_detect_lang_invalid_param_preserves_cookie():
    s = State()
    s.lang = "pt"  # non-default cookie language
    object.__setattr__(s, "router", _FakeRouter(query={"lang": "zz"}))
    s.detect_lang()
    assert s.lang == "pt"


def test_detect_lang_accept_language_quality():
    s = State()
    s.lang = "en"  # default
    object.__setattr__(
        s,
        "router",
        _FakeRouter(query={}, headers={"accept-language": "pt-BR,pt;q=0.9,en;q=0.8"}),
    )
    s.detect_lang()
    assert s.lang == "pt"


def test_detect_lang_swallows_missing_router():
    s = State()
    object.__setattr__(s, "router", None)
    s.detect_lang()  # must not raise
    assert s.lang in ("en", "pt")


# ---------------------------------------------------------------------------
# reset_intake
# ---------------------------------------------------------------------------

def test_reset_intake_clears_all_and_redirects():
    s = State()
    s.step = 6
    s.chief_complaint = "Headache"
    s.session_id = "sess_123"
    s.questions = ["Q1"]
    s.current_answers = ["A1"]
    s.is_emergency = True
    events = list(s.reset_intake())
    assert s.step == 0
    assert s.chief_complaint == ""
    assert s.session_id == ""
    assert s.questions == []
    assert s.current_answers == []
    assert s.is_emergency is False
    assert len(events) == 3  # clear-draft + scroll-top + redirect


# ---------------------------------------------------------------------------
# get_interview_questions (background handler) — stream parsing & branches
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_interview_questions_happy_path():
    s = State()
    s.session_id = "sess-9"
    s.lang = "en"
    s.loading = False

    client = routed_client({
        "/api/interview-questions-stream": lambda r: httpx.Response(
            200, text=sse("1. Pain in the chest?\n2. Does it spread?")
        ),
    })
    with patch("httpx.AsyncClient", return_value=client):
        await State.get_interview_questions.fn(s)

    assert s.questions == ["Pain in the chest?", "Does it spread?"]
    assert s.error_message == ""
    assert s.is_emergency is False


@pytest.mark.asyncio
async def test_get_interview_questions_emergency_red_flag():
    s = State()
    s.session_id = "sess-9"
    s.lang = "en"

    client = routed_client({
        "/api/interview-questions-stream": lambda r: httpx.Response(
            200, text=sse("[EMERGENCY ALERT] Please call 911 immediately.")
        ),
    })
    with patch("httpx.AsyncClient", return_value=client):
        await State.get_interview_questions.fn(s)

    assert s.is_emergency is True
    assert s.questions == []
    assert s.current_answers == []


@pytest.mark.asyncio
async def test_get_interview_questions_timeout():
    s = State()
    s.session_id = "sess-9"
    s.lang = "en"

    def route(_):
        raise asyncio.TimeoutError()

    client = routed_client({"/api/interview-questions-stream": route})
    with patch("httpx.AsyncClient", return_value=client):
        await State.get_interview_questions.fn(s)

    assert s.error_message == s._t["err_timeout"]


@pytest.mark.asyncio
async def test_get_interview_questions_generic_error():
    s = State()
    s.session_id = "sess-9"
    s.lang = "en"

    def route(_):
        raise httpx.ConnectError("down")

    client = routed_client({"/api/interview-questions-stream": route})
    with patch("httpx.AsyncClient", return_value=client):
        await State.get_interview_questions.fn(s)

    assert s.error_message == s._t["err_stream"]


@pytest.mark.asyncio
async def test_get_interview_questions_malformed_json():
    s = State()
    s.session_id = "sess-9"
    s.lang = "en"

    client = routed_client({
        "/api/interview-questions-stream": lambda r: httpx.Response(
            200, text="data: not-json\n\n"
        ),
    })
    with patch("httpx.AsyncClient", return_value=client):
        await State.get_interview_questions.fn(s)

    assert s.error_message == s._t["err_stream"]


# ---------------------------------------------------------------------------
# submit_answers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_answers_requires_all_answered():
    s = State()
    s.step = 5  # interview step
    s.questions = ["Q1", "Q2"]
    s.current_answers = ["a", ""]
    events = [x async for x in s.submit_answers()]
    assert events == []
    assert s.step == 5  # stays put; no transition
    assert s.error_message == s._t["err_followup_ans"]


@pytest.mark.asyncio
async def test_submit_answers_builds_summary():
    s = State()
    s.questions = ["Q1", "Q2"]
    s.current_answers = ["A1", "A2"]
    s.specialist = "Cardiology"
    s.chief_complaint = "Chest pain"
    events = [x async for x in s.submit_answers()]
    assert s.step == 6
    assert "Q1" in s.summary_text
    assert "A1" in s.summary_text
    assert "Cardiology" in s.summary_text
    assert len(events) == 2


# ---------------------------------------------------------------------------
# download_report (background handler)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_download_report_success():
    s = State()
    s.session_id = "sess-9"
    s.questions = ["Q1"]
    s.current_answers = ["A1"]

    client = routed_client({"/api/generate-pdf": lambda r: httpx.Response(200, content=b"%PDF-real")})
    with patch("httpx.AsyncClient", return_value=client):
        events = await State.download_report.fn(s)

    assert s.error_message == ""
    assert events is not None
    assert len(events) == 3  # gtag call + clear-draft + download


@pytest.mark.asyncio
async def test_download_report_non_200():
    s = State()
    s.session_id = "sess-9"
    s.questions = ["Q1"]
    s.current_answers = ["A1"]

    client = routed_client({"/api/generate-pdf": lambda r: httpx.Response(500, text="")})
    with patch("httpx.AsyncClient", return_value=client):
        events = await State.download_report.fn(s)

    assert events is None
    assert s.error_message == s._t["err_download"]


@pytest.mark.asyncio
async def test_download_report_exception():
    s = State()
    s.session_id = "sess-9"
    s.questions = ["Q1"]
    s.current_answers = ["A1"]

    def route(_):
        raise httpx.ConnectError("down")

    client = routed_client({"/api/generate-pdf": route})
    with patch("httpx.AsyncClient", return_value=client):
        events = await State.download_report.fn(s)

    assert events is None
    assert s.error_message == s._t["err_download_gen"]


# ---------------------------------------------------------------------------
# AdminState token gating
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_access_denied_without_token(monkeypatch):
    monkeypatch.setenv("ADMIN_DASHBOARD_TOKEN", "secret")
    state = AdminState()
    object.__setattr__(state, "router", _FakeRouter(query={}))
    await state.load_analytics()
    assert state.authorized is False
    assert state.analytics_data == []


@pytest.mark.asyncio
async def test_admin_access_granted_with_token(monkeypatch):
    import reflex_app.preconsult.state as st

    monkeypatch.setenv("ADMIN_DASHBOARD_TOKEN", "secret")
    state = AdminState()
    object.__setattr__(state, "router", _FakeRouter(query={"token": "secret"}))
    # Patch the module-level analytics fetcher (the class method routes through
    # reflex's method-proxy machinery and cannot be patched reliably).
    api_mock = AsyncMock(return_value=[{"date": "x"}])
    with patch.object(st, "fetch_analytics_data", api_mock):
        await state.load_analytics()
    assert state.authorized is True
    assert state.analytics_data == [{"date": "x"}]
    api_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# _get_router_params helper
# ---------------------------------------------------------------------------

def test_get_router_params_returns_empty_for_none():
    assert _get_router_params(None) == {}


def test_get_router_params_query_parameters():
    router = _FakeRouter(query={"lang": "pt"})
    assert _get_router_params(router) == {"lang": "pt"}
