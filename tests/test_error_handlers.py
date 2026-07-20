import pytest
from unittest.mock import patch, AsyncMock
import httpx
from httpx import ASGITransport
from preconsult.main import app
from google.api_core.exceptions import GoogleAPIError
from preconsult.core.errors import RedisUnavailableError

HEADERS = {"X-API-KEY": "ci_test_key_123"}
FULL_PAYLOAD = {
    "age_bracket": "26-35",
    "sex": "Female",
    "lang": "en",
    "specialist": "Cardiology",
    "chief_complaint": "Chest pain",
    "duration": "2 days",
    "smoking": "No",
    "alcohol": "No",
}


@pytest.mark.asyncio
async def test_validation_error_missing_field_returns_422():
    payload = {k: v for k, v in FULL_PAYLOAD.items() if k != "age_bracket"}
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/session/init", json=payload, headers=HEADERS)
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_validation_error_empty_qa_pairs_returns_422():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/generate-pdf", json={"session_id": "x", "qa_pairs": []}, headers=HEADERS)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_validation_error_long_chief_complaint_returns_422():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/initial-questions-stream", json={"session_id": "x", "chief_complaint": "a" * 5001}, headers=HEADERS)
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("preconsult.api.endpoints.check_session_quota", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.check_rate_limit", new_callable=AsyncMock)
@patch("preconsult.api.endpoints.create_session", new_callable=AsyncMock)
async def test_redis_unavailable_returns_503(mock_create, mock_rate, mock_quota):
    mock_quota.return_value = True
    mock_rate.return_value = True
    mock_create.side_effect = RedisUnavailableError("Redis is down")

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/session/init", json=FULL_PAYLOAD, headers=HEADERS)
    assert response.status_code == 503
    assert "indisponivel" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_api_error_during_startup_returns_502():
    import preconsult.services.agent_service as agent_service
    import preconsult.core.llm as llm_module
    agent_service._interview_chain = None
    llm_module._llm = None
    from preconsult.core.llm import get_llm

    original_llm = llm_module._llm
    llm_module._llm = None
    with patch("preconsult.core.llm.ChatVertexAI") as mock_chat:
        mock_chat.side_effect = GoogleAPIError("Vertex AI quota exceeded")
        with pytest.raises(GoogleAPIError):
            get_llm()
    llm_module._llm = original_llm


@pytest.mark.asyncio
async def test_generic_error_returns_500():
    import preconsult.services.session_service as srv
    srv._redis_available = False
    await srv._memory_limiter.clear()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/session/init", json={}, headers=HEADERS)
    assert response.status_code in (422, 500)


@pytest.mark.asyncio
async def test_validation_error_wrong_type_for_list_field_returns_422():
    payload = {**FULL_PAYLOAD, "conditions": "not_a_list"}
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/session/init", json=payload, headers=HEADERS)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_validation_error_long_answer_returns_422():
    payload = {"session_id": "x", "qa_pairs": [{"question": "?", "answer": "a" * 2001}]}
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/generate-pdf", json=payload, headers=HEADERS)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_llm_raises_on_init_failure():
    import preconsult.core.llm as llm_module
    llm_module._llm = None
    with patch("preconsult.core.llm.ChatVertexAI") as mock_chat:
        mock_chat.side_effect = GoogleAPIError("Vertex AI quota exceeded")
        with pytest.raises(GoogleAPIError):
            llm_module.get_llm()
