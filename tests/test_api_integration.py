import pytest
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from httpx import ASGITransport
from preconsult.main import app

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
        yield "1. Question?"
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
        yield "1. Question?"
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
        yield "1. Question?"
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
        yield "1. Happy Question?"
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
        resp = await client.post("/api/analytics/event", json={"event": "test_event"}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    expected_key = f"analytics:{date.today().isoformat()}"
    mock_client.hincrby.assert_called_once_with(expected_key, "test_event", 1)
    mock_client.expire.assert_called_once()


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


@pytest.mark.asyncio
async def test_health_reports_unavailable_when_redis_unknown():
    from preconsult.services.session_service import _redis_available
    original = _redis_available
    try:
        import preconsult.services.session_service as svc
        svc._redis_available = None
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["redis"] == "unavailable"
    finally:
        svc._redis_available = original


@pytest.mark.asyncio
async def test_root_endpoint():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/", headers=HEADERS)
    assert resp.status_code == 200
    assert "Welcome" in resp.json()["message"]


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
    from preconsult.services.session_service import _redis_available, _memory_limiter
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
    from preconsult.services.session_service import _redis_available, _memory_limiter
    original = _redis_available
    try:
        import preconsult.services.session_service as svc
        svc._redis_available = False
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/analytics/event", json={"event": "test"}, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
    finally:
        svc._redis_available = original
