import pytest
import json
from unittest.mock import patch, AsyncMock
import httpx
from httpx import ASGITransport
from preconsult.host import app
from preconsult.services.agent_service import StreamEvent

HEADERS = {"X-API-KEY": "ci_test_key_123"}

FULL_SESSION_PAYLOAD = {
    "age_bracket": "26-35",
    "sex": "Female",
    "lang": "en",
    "specialist": "Gastroenterologist",
    "chief_complaint": "Stomach pain and heartburn",
    "duration": "Weeks",
    "complaint_detail": "Gets worse at night",
    "conditions": [],
    "medications": [],
    "allergies": "",
    "family_history": [],
    "smoking": "Never smoked",
    "alcohol": "Rarely",
}

FULL_SESSION_DATA = {**FULL_SESSION_PAYLOAD}

@pytest.mark.asyncio
@patch("preconsult.api.endpoints.create_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_session_quota", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.increment_session_quota", new_callable=AsyncMock)
async def test_init_session(mock_inc, mock_quota, mock_rate, mock_create):
    mock_create.return_value = "fake-session-id"
    mock_quota.return_value = True
    mock_rate.return_value = True
    
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/session/init", json=FULL_SESSION_PAYLOAD, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["session_id"] == "fake-session-id"
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_init_session_degrades_to_memory_when_redis_quota_exceeded():
    """When Upstash rejects writes with 'max requests limit exceeded', session/init
    must STILL succeed (degraded to the per-worker in-memory store), not block the
    user over infrastructure."""

    def quota_fail(*args, **kwargs):
        raise Exception("max requests limit exceeded. Limit: 500000")

    class FakeRedis:
        async def eval(self, *a, **k): quota_fail()
        async def get(self, *a, **k): return None
        async def hset(self, *a, **k): quota_fail()
        async def expire(self, *a, **k): quota_fail()

    import preconsult.services.session_service as srv
    with patch.object(srv, "get_redis", return_value=FakeRedis()):
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/session/init", json=FULL_SESSION_PAYLOAD, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["session_id"]

@pytest.mark.asyncio
@patch("preconsult.api.endpoints.create_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_session_quota", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.increment_session_quota", new_callable=AsyncMock)
async def test_init_session_with_full_form(mock_inc, mock_quota, mock_rate, mock_create):
    mock_create.return_value = "fake-session-id"
    mock_quota.return_value = True
    mock_rate.return_value = True

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/session/init", json=FULL_SESSION_PAYLOAD, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["session_id"] == "fake-session-id"
    mock_create.assert_called_once()
    stored = mock_create.call_args[0][0]
    assert stored["age_bracket"] == "26-35"

@pytest.mark.asyncio
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
async def test_interview_questions_stream(mock_chain, mock_rate, mock_stream, mock_get):
    mock_get.return_value = FULL_SESSION_DATA
    mock_rate.return_value = True
    async def fake_stream(*args, **kwargs):
        yield StreamEvent(kind="text", value="1. Question?")
    mock_stream.side_effect = fake_stream

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/interview-questions-stream", json={"session_id": "fake-id"}, headers=HEADERS) as response:
            assert response.status_code == 200
            full_text = ""
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    full_text += json.loads(line[len("data:"):].strip())
            assert "Question" in full_text
            assert mock_stream.called


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.update_session", new_callable=AsyncMock)
async def test_initial_questions_stream(mock_update, mock_chain, mock_rate, mock_get, mock_stream):
    mock_get.return_value = {"lang": "en", "chief_complaint": "pain"}
    mock_rate.return_value = True
    async def fake_stream(*args, **kwargs):
        yield StreamEvent(kind="text", value="1. Question?")
    mock_stream.side_effect = fake_stream

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/initial-questions-stream", json={"session_id": "fake-id", "chief_complaint": "  pain  "}, headers=HEADERS) as response:
            assert response.status_code == 200
            full_text = ""
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    full_text += json.loads(line[len("data:"):].strip())
            assert "Question" in full_text
            assert mock_stream.called


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
async def test_initial_questions_stream_session_not_found(mock_chain, mock_rate):
    mock_rate.return_value = True
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/initial-questions-stream", json={"session_id": "bad-id", "chief_complaint": "pain"}, headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.update_session", new_callable=AsyncMock)
async def test_initial_questions_stream_sanitizes_input(mock_update, mock_chain, mock_rate, mock_get, mock_stream):
    mock_get.return_value = {"lang": "en", "chief_complaint": "pain"}
    mock_rate.return_value = True
    async def fake_stream(*args, **kwargs):
        yield StreamEvent(kind="text", value="1. Question?")
    mock_stream.side_effect = fake_stream

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/api/initial-questions-stream", json={"session_id": "fake-id", "chief_complaint": "  chest pain  "}, headers=HEADERS) as response:
            assert response.status_code == 200
            await response.aread()
            update_call = mock_update.call_args
            assert update_call is not None
            assert update_call[0][1]["chief_complaint"] == "chest pain"

@pytest.mark.asyncio
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
async def test_interview_stream_session_not_found(mock_chain, mock_rate, mock_get):
    mock_get.return_value = {}
    mock_rate.return_value = True
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/interview-questions-stream", json={"session_id": "bad-id"}, headers=HEADERS)
    assert response.status_code == 404

@pytest.mark.asyncio
@patch("preconsult.api.endpoints.check_rate_limit", return_value=True)
async def test_interview_stream_redis_unavailable_not_expired(mock_rate):
    """When Redis is down and there's no in-memory fallback, surface a real
    redis_unavailable (503), NOT a misleading 'session expired' (404)."""
    from preconsult.core.errors import RedisUnavailableError
    with patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = RedisUnavailableError("redis down")
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/interview-questions-stream", json={"session_id": "any"}, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == "redis_unavailable"


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.check_rate_limit", return_value=True)
async def test_interview_stream_redis_quota_exceeded(mock_rate):
    """An exhausted Upstash quota surfaces its own code, distinct from a general
    outage, so it can be alerted on specifically."""
    from preconsult.core.errors import RedisQuotaExceededError
    with patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = RedisQuotaExceededError("quota")
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/interview-questions-stream", json={"session_id": "any"}, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["code"] == "redis_quota_exceeded"


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.generate_pdf_report_in_memory")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", return_value=True)
async def test_generate_pdf_with_qa_pairs(mock_rate, mock_get, mock_pdf):
    mock_get.return_value = FULL_SESSION_DATA
    mock_pdf.return_value = (b"%PDF-fake-pdf-content", "Medical_Summary_Report.pdf")

    payload = {
        "session_id": "fake-id",
        "qa_pairs": [{"question": "Where is the pain?", "answer": "Upper abdomen"}],
    }
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/generate-pdf", json=payload, headers=HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")

@pytest.mark.asyncio
@patch("preconsult.api.endpoints.generate_pdf_report_in_memory")
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.create_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_session_quota", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.increment_session_quota", new_callable=AsyncMock)
async def test_full_session_happy_path(mock_inc, mock_quota, mock_rate, mock_create, mock_get, mock_stream, mock_pdf):
    mock_create.return_value = "happy-session-id"
    mock_quota.return_value = True
    mock_rate.return_value = True
    mock_get.return_value = FULL_SESSION_DATA
    async def fake_stream(*args, **kwargs):
        yield StreamEvent(kind="text", value="1. Happy Question?")
    mock_stream.side_effect = fake_stream
    mock_pdf.return_value = (b"%PDF-happy-pdf", "Report.pdf")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Init
        resp1 = await client.post("/api/session/init", json=FULL_SESSION_PAYLOAD, headers=HEADERS)
        assert resp1.status_code == 200
        
        # 2. Stream
        async with client.stream("POST", "/api/interview-questions-stream", json={"session_id": "happy-session-id"}, headers=HEADERS) as resp2:
            assert resp2.status_code == 200
            full_text = ""
            async for line in resp2.aiter_lines():
                if line.startswith("data:"):
                    full_text += json.loads(line[len("data:"):].strip())
            assert "Happy Question" in full_text
            
        # 3. PDF
        payload = {
            "session_id": "happy-session-id",
            "qa_pairs": [{"question": "Happy?", "answer": "Yes"}],
        }
        resp3 = await client.post("/api/generate-pdf", json=payload, headers=HEADERS)
        assert resp3.status_code == 200
        assert resp3.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_missing_api_key_returns_403():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/session/init", json=FULL_SESSION_PAYLOAD)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_wrong_api_key_returns_403():
    headers = {"X-API-KEY": "wrong_key"}
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/session/init", json=FULL_SESSION_PAYLOAD, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.get_redis")
async def test_analytics_event_endpoint(mock_get_redis):
    from datetime import date
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/analytics/event", json={"event": "lifestyle_submitted"}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    expected_key = f"analytics:{date.today().isoformat()}"
    mock_client.hincrby.assert_called_once_with(expected_key, "lifestyle_submitted", 1)
    mock_client.expire.assert_called_once()


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.get_redis")
async def test_anonymous_funnel_event_counts_in_memory_not_redis(mock_get_redis):
    """Pre-session steps have no session to key on and must not spend Redis."""
    from preconsult.core.observability import snapshot_counters

    before = snapshot_counters().get("funnel.intake_started", 0)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/analytics/event", json={"event": "intake_started"}, headers=HEADERS)
    assert resp.status_code == 200
    assert snapshot_counters().get("funnel.intake_started", 0) == before + 1
    mock_get_redis.assert_not_called()


def test_every_funnel_key_is_assigned_to_exactly_one_tier():
    """A new key must pick a tier deliberately, not default into Redis."""
    from typing import get_args

    from preconsult.api.endpoints import (
        ANONYMOUS_FUNNEL_EVENTS,
        SESSION_FUNNEL_EVENTS,
        FunnelEvent,
    )

    assert set(get_args(FunnelEvent)) == set(ANONYMOUS_FUNNEL_EVENTS) | set(
        SESSION_FUNNEL_EVENTS
    )
    assert not set(ANONYMOUS_FUNNEL_EVENTS) & set(SESSION_FUNNEL_EVENTS)


@pytest.mark.asyncio
async def test_unknown_analytics_event_is_rejected():
    """The whitelist bounds the Redis hash fields to the documented keys."""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/analytics/event", json={"event": "made_up_key"}, headers=HEADERS)
    assert resp.status_code == 422


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.get_redis")
async def test_analytics_stats_endpoint(mock_get_redis):
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "demographics_submitted": "5",
        "complaint_submitted": "3",
        "pdf_downloaded": "1",
    }
    mock_get_redis.return_value = mock_client

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/analytics/stats", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7
    assert data[-1]["demographics"] == 5
    assert data[-1]["pdf"] == 1


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    # /health reports the interactive-channel status. The Reflex-free app has no
    # socket, so it answers "not_configured" rather than pretending.
    assert body["event_channel"] in ("ok", "unavailable", "not_configured")


@pytest.mark.asyncio
async def test_health_event_channel_uses_the_injected_probe():
    """/health must surface the interactive channel when a probe is wired in.

    The probe is bound per app (see register_health_routes), so this builds an
    app with one instead of patching a module global: a global would make the
    answer depend on import order.
    """
    from preconsult.host import build_asgi_app

    probe = AsyncMock(return_value="ok")
    probed_app = build_asgi_app(event_channel_probe=probe)

    async with httpx.AsyncClient(transport=ASGITransport(app=probed_app), base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["event_channel"] == "ok"
    probe.assert_awaited_once()


@pytest.mark.asyncio
@patch("preconsult.services.session_service.check_redis_status", new_callable=AsyncMock)
async def test_health_reports_ok_when_redis_up(mock_status):
    mock_status.return_value = "ok"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["redis"] == "ok"


@pytest.mark.asyncio
@patch("preconsult.services.session_service.check_redis_status", new_callable=AsyncMock)
async def test_health_reports_unavailable_when_redis_down(mock_status):
    mock_status.return_value = "unavailable"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["redis"] == "unavailable"


@pytest.mark.asyncio
@patch("preconsult.services.session_service.check_redis_status", new_callable=AsyncMock)
async def test_health_reports_quota_exceeded(mock_status):
    """An exhausted Upstash quota is surfaced explicitly, not as a generic outage."""
    mock_status.return_value = "quota_exceeded"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["redis"] == "quota_exceeded"
    assert body["code"] == "redis_quota_exceeded"


@pytest.mark.asyncio
async def test_health_live_always_ready():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
@patch("preconsult.services.session_service.check_redis_status", new_callable=AsyncMock)
async def test_health_ready_200_when_redis_ok(mock_status):
    mock_status.return_value = "ok"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["redis"] == "ok"


@pytest.mark.asyncio
@patch("preconsult.services.session_service.check_redis_status", new_callable=AsyncMock)
async def test_health_ready_503_when_redis_down(mock_status):
    mock_status.return_value = "unavailable"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["code"] == "service_unavailable"


@pytest.mark.asyncio
@patch("preconsult.services.session_service.check_redis_status", new_callable=AsyncMock)
async def test_health_ready_503_code_quota_when_quota_exceeded(mock_status):
    """/health/ready maps quota exhaustion to its own code, not generic unavailable."""
    mock_status.return_value = "quota_exceeded"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["code"] == "redis_quota_exceeded"


@pytest.mark.asyncio
@patch("preconsult.services.session_service.check_redis_status", new_callable=AsyncMock)
async def test_health_probe_is_throttled_not_per_request(mock_status):
    """Frequent /health hits must not re-probe Redis/socket on every request.

    This is what reserved the serverless Redis quota for real users instead of
    letting health/CI/scanner polling burn it. The real throttled wrapper should
    call the underlying Redis check exactly once across three /health requests.
    """
    from preconsult.host import build_asgi_app

    mock_status.return_value = "ok"
    probe = AsyncMock(return_value="ok")
    probed_app = build_asgi_app(event_channel_probe=probe)

    async with httpx.AsyncClient(transport=ASGITransport(app=probed_app), base_url="http://test") as client:
        for _ in range(3):
            resp = await client.get("/health")
            assert resp.status_code == 200

    # The throttle cache means each real probe fired once, not three times.
    assert mock_status.await_count == 1
    assert probe.await_count == 1


@pytest.mark.asyncio
async def test_root_endpoint():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_robots_txt_endpoint():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "Disallow: /admin/" in resp.text


@pytest.mark.asyncio
async def test_sitemap_xml_endpoint():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert 'hreflang="en"' in resp.text


@pytest.mark.asyncio
async def test_llms_txt_endpoint():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/llms.txt")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "PreConsult" in resp.text


@pytest.mark.asyncio
async def test_analytics_stats_empty_when_redis_down():
    from preconsult.services.session_service import _redis_available
    original = _redis_available
    try:
        import preconsult.services.session_service as svc
        svc._redis_available = False
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/analytics/stats", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        svc._redis_available = original


@pytest.mark.asyncio
async def test_analytics_event_still_ok_when_redis_down():
    from preconsult.services.session_service import _redis_available
    original = _redis_available
    try:
        import preconsult.services.session_service as svc
        svc._redis_available = False
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/analytics/event", json={"event": "summary_generated"}, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
    finally:
        svc._redis_available = original


# ---------------------------------------------------------------------------
# Input-side emergency gate (deterministic red flag on the chief complaint)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.update_session", new_callable=AsyncMock)
async def test_initial_stream_emergency_input_short_circuits_llm(
    mock_update, mock_chain, mock_rate, mock_get, mock_stream
):
    """A red flag in the patient's own description must warn immediately,
    WITHOUT calling the LLM (so safety never depends on the model)."""
    mock_get.return_value = {"lang": "en", "chief_complaint": "pain"}
    mock_rate.return_value = True

    async def fake_stream(*args, **kwargs):
        raise AssertionError("LLM stream must not be called on input red flag")
        yield  # pragma: no cover

    mock_stream.side_effect = fake_stream

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/initial-questions-stream",
            json={"session_id": "x", "chief_complaint": "severe chest pain, call 911"},
            headers=HEADERS,
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            body = "".join([line async for line in response.aiter_text()])

    assert "data: " in body
    assert "EMERGENCY" in body.upper()
    assert not mock_stream.called


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
async def test_interview_stream_emergency_input_short_circuits_llm(
    mock_chain, mock_rate, mock_get, mock_stream
):
    """Same deterministic gate on the full-context interview stream."""
    mock_get.return_value = {"lang": "pt", "chief_complaint": "dor no peito, urgência"}
    mock_rate.return_value = True

    async def fake_stream(*args, **kwargs):
        raise AssertionError("LLM stream must not be called on input red flag")
        yield  # pragma: no cover

    mock_stream.side_effect = fake_stream

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/api/interview-questions-stream", json={"session_id": "x"}, headers=HEADERS
        ) as response:
            assert response.status_code == 200
            body = "".join([line async for line in response.aiter_text()])

    # SSE payload is JSON-encoded; decode exactly like the real client consumer.
    payload_line = next(ln for ln in body.split("\n") if ln.startswith("data: "))
    decoded = json.loads(payload_line[len("data: "):])
    assert "ALERTA DE EMERGÊNCIA" in decoded
    assert not mock_stream.called


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.stream_interview_questions")
@patch("preconsult.api.endpoints.get_session", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.get_interview_chain", new_callable=AsyncMock)
async def test_interview_stream_non_emergency_still_calls_llm(
    mock_chain, mock_rate, mock_get, mock_stream
):
    """A benign complaint must NOT be short-circuited by the input gate."""
    mock_get.return_value = {"lang": "en", "chief_complaint": "stomach pain"}
    mock_rate.return_value = True

    async def fake_stream(*args, **kwargs):
        yield StreamEvent(kind="text", value="1. Where is the pain?")

    mock_stream.side_effect = fake_stream

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/api/interview-questions-stream", json={"session_id": "x"}, headers=HEADERS
        ) as response:
            body = "".join([line async for line in response.aiter_text()])

    assert "Where is the pain?" in body
    assert mock_stream.called


def test_emergency_message_defaults_to_english_for_unknown_lang():
    from preconsult.api.endpoints import _emergency_message

    assert "EMERGENCY" in _emergency_message("xx")
    assert "EMERGENCY" in _emergency_message("en")
    assert "EMERGÊNCIA" in _emergency_message("pt")
