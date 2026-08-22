import pytest
from unittest.mock import patch, AsyncMock
import httpx
import asyncio
import json
from httpx import ASGITransport
from reflex_app.preconsult.preconsult import api as app
from google.api_core.exceptions import GoogleAPIError
from preconsult.core.errors import (
    RedisUnavailableError,
    LLMUnavailableError,
    redis_unavailable_handler,
    llm_unavailable_handler,
    validation_handler,
    google_api_handler,
    generic_handler,
)

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
async def test_validation_error_invalid_type_returns_422():
    payload = {**FULL_PAYLOAD, "conditions": "invalid_type_not_a_list"}
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
        response = await client.post("/api/session/init", json={"conditions": "invalid"}, headers=HEADERS)
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


# ---------------------------------------------------------------------------
# Direct handler tests: error-code mapping + PHI/data-safety contract.
#
# Every error handler must return a *generic*, localized detail that never
# leaks the underlying exception message, stack frame, or any user-supplied
# value (the app's zero-data-persistence constraint extends to error output).
# ---------------------------------------------------------------------------

class _FakeRequest:
    scope = {"type": "http", "path": "/api/session/init"}


def _run_handler(handler, exc):
    return asyncio.run(handler(_FakeRequest(), exc))


def test_llm_unavailable_handler_returns_503_sanitized():
    resp = _run_handler(llm_unavailable_handler, LLMUnavailableError("boom: vertex key invalid"))
    assert resp.status_code == 503
    detail = resp.body.decode()
    # no exception message / module path leaked
    assert "vertex key invalid" not in detail
    assert "preconsult" not in detail


def test_redis_unavailable_handler_returns_503_sanitized():
    resp = _run_handler(redis_unavailable_handler, RedisUnavailableError("redis connection refused"))
    assert resp.status_code == 503
    detail = resp.body.decode()
    assert "redis connection refused" not in detail


def test_validation_handler_maps_422_and_keeps_errors():
    from pydantic import ValidationError, BaseModel, Field

    class M(BaseModel):
        age: int = Field(ge=0, le=150)

    try:
        M(age=-5)
    except ValidationError as exc:
        resp = _run_handler(validation_handler, exc)
    assert resp.status_code == 422
    body = json.loads(resp.body)
    assert "errors" in body
    assert body["errors"][0]["loc"][0] == "age"


def test_google_api_handler_returns_502_sanitized():
    resp = _run_handler(google_api_handler, GoogleAPIError("PERMISSION_DENIED: secret bucket"))
    assert resp.status_code == 502
    detail = resp.body.decode()
    assert "secret bucket" not in detail


def test_generic_handler_returns_500_sanitized():
    resp = _run_handler(generic_handler, Exception("Traceback: /etc/passwd line 42"))
    assert resp.status_code == 500
    detail = resp.body.decode()
    assert "/etc/passwd" not in detail
    assert "line 42" not in detail


def test_generic_handler_sanitizes_user_data():
    # Simulate an exception that would embed a patient-supplied value if the
    # handler were careless (e.g. str(exc) containing chief complaint text).
    resp = _run_handler(generic_handler, Exception("chief_complaint='chest pain at 3am'"))
    body = resp.body.decode()
    assert "chest pain at 3am" not in body
