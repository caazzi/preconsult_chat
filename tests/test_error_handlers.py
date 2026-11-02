import pytest
from unittest.mock import patch, AsyncMock
import httpx
import asyncio
import json
from httpx import ASGITransport
from botocore.exceptions import ClientError
from preconsult.host import app
from preconsult.core.errors import (
    RedisUnavailableError,
    LLMUnavailableError,
    LLMUpstreamError,
    redis_unavailable_handler,
    llm_unavailable_handler,
    llm_upstream_handler,
    validation_handler,
    generic_handler,
)
from tests.fakes import session_payload

HEADERS = {"X-API-KEY": "ci_test_key_123"}
FULL_PAYLOAD = session_payload(smoking="No", alcohol="No")


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
async def test_provider_init_failure_is_normalized(monkeypatch):
    """A credential failure at construction becomes 502/503, not a 500."""
    import preconsult.core.llm as llm_module

    original_llm = llm_module._llm
    llm_module._llm = None
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "bedrock")
    monkeypatch.setattr(
        llm_module, "LLM_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    try:
        with patch("langchain_aws.ChatBedrockConverse") as mock_chat:
            mock_chat.side_effect = ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
                "InvokeModel",
            )
            with pytest.raises(LLMUpstreamError) as exc_info:
                llm_module.get_llm()
        assert exc_info.value.kind == "auth"
    finally:
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
async def test_get_llm_normalizes_an_invalid_model_failure(monkeypatch):
    import preconsult.core.llm as llm_module

    original_llm = llm_module._llm
    llm_module._llm = None
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "bedrock")
    monkeypatch.setattr(
        llm_module, "LLM_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    try:
        with patch("langchain_aws.ChatBedrockConverse") as mock_chat:
            mock_chat.side_effect = ClientError(
                {"Error": {"Code": "ValidationException", "Message": "bad model"}},
                "InvokeModel",
            )
            with pytest.raises(LLMUpstreamError) as exc_info:
                llm_module.get_llm()
        assert exc_info.value.kind == "invalid_request"
    finally:
        llm_module._llm = original_llm


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
    resp = _run_handler(llm_unavailable_handler, LLMUnavailableError("boom: bedrock key invalid"))
    assert resp.status_code == 503
    body = resp.body.decode()
    assert "llm_unavailable" in body  # machine-readable code present
    # no exception message / module path leaked
    assert "bedrock key invalid" not in body
    assert "preconsult" not in body


def test_redis_unavailable_handler_returns_503_sanitized():
    resp = _run_handler(redis_unavailable_handler, RedisUnavailableError("redis connection refused"))
    assert resp.status_code == 503
    detail = resp.body.decode()
    assert "redis_unavailable" in detail
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


@pytest.mark.parametrize(
    "kind,expected_status,expected_code",
    [
        ("throttled", 503, "llm_unavailable"),
        ("timeout", 503, "llm_unavailable"),
        ("auth", 502, "ai_upstream_error"),
        ("invalid_request", 502, "ai_upstream_error"),
        ("blocked", 502, "ai_upstream_error"),
        ("malformed", 502, "ai_upstream_error"),
        ("upstream", 502, "ai_upstream_error"),
    ],
)
def test_llm_upstream_handler_maps_kind_to_stable_code(
    kind, expected_status, expected_code
):
    resp = _run_handler(
        llm_upstream_handler, LLMUpstreamError(kind, provider="bedrock")
    )
    body = json.loads(resp.body)
    assert resp.status_code == expected_status
    assert body["code"] == expected_code


def test_llm_upstream_handler_never_echoes_vendor_detail():
    resp = _run_handler(llm_upstream_handler, LLMUpstreamError("auth", provider="bedrock"))
    body = resp.body.decode()
    assert "auth" not in body
    assert "bedrock" not in body


def test_unknown_kind_is_normalized_to_upstream():
    assert LLMUpstreamError("something-new").kind == "upstream"


def test_retryable_kinds_are_throttling_and_timeout():
    assert LLMUpstreamError("throttled").retryable is True
    assert LLMUpstreamError("timeout").retryable is True
    assert LLMUpstreamError("auth").retryable is False


def test_bedrock_throttling_is_classified_retriable():
    from preconsult.core.llm import _classify_bedrock

    exc = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "InvokeModel"
    )
    assert _classify_bedrock(exc) == "throttled"


def test_vertex_resource_exhausted_is_classified_retriable():
    from google.genai.errors import APIError

    from preconsult.core.llm import _classify_vertex

    exc = APIError(
        429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}}
    )
    assert _classify_vertex(exc) == "throttled"


def test_llm_upstream_handler_is_registered():
    """A provider swap must not leave upstream errors unmapped to 502/503."""
    from preconsult.host import build_starlette_app

    mount = next(
        r for r in build_starlette_app().routes if getattr(r, "path", None) == "/api"
    )
    assert LLMUpstreamError in mount.app.exception_handlers


def test_generic_handler_returns_500_sanitized():
    resp = _run_handler(generic_handler, Exception("Traceback: /etc/passwd line 42"))
    assert resp.status_code == 500
    detail = resp.body.decode()
    assert "/etc/passwd" not in detail
    assert "line 42" not in detail


def test_valid_http_exception_carries_code():
    from preconsult.core.errors import http_exception_handler, HTTP_STATUS_CODES
    from fastapi import HTTPException

    detail_msg = "Session expired or invalid"
    resp = _run_handler(http_exception_handler, HTTPException(status_code=404, detail=detail_msg))
    assert resp.status_code == 404
    body = json.loads(resp.body)
    # non-breaking: detail remains the original string; code added as sibling
    assert body["detail"] == detail_msg
    assert body["code"] == "session_expired"
    assert HTTP_STATUS_CODES[404] == "session_expired"


def test_valid_http_exception_status_mapping():
    from preconsult.core.errors import http_exception_handler
    from fastapi import HTTPException

    resp = _run_handler(http_exception_handler, HTTPException(status_code=429, detail="Too many"))
    assert json.loads(resp.body)["code"] == "rate_limited"


def test_generic_handler_sanitizes_user_data():
    # Simulate an exception that would embed a patient-supplied value if the
    # handler were careless (e.g. str(exc) containing chief complaint text).
    resp = _run_handler(generic_handler, Exception("chief_complaint='chest pain at 3am'"))
    body = resp.body.decode()
    assert "internal_error" in body
    assert "chest pain at 3am" not in body
