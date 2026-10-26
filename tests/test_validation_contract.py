"""Contract tests for 422 request-validation responses.

FastAPI raises ``RequestValidationError`` (not pydantic's ``ValidationError``)
for bad request bodies, and its error details embed the submitted value under
``input`` plus a ``ctx`` payload. Both can carry PHI, so the handler must strip
them from the response *and* from the logs while keeping the stable
``validation_failed`` code.

The handler is wired into the app in a later wave, so these tests call it
directly with a ``RequestValidationError`` shaped exactly like FastAPI's
(``loc`` prefixed with ``"body"``). Route-level assertions belong to the
wiring change.
"""

import asyncio
import json
import logging

import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError

from preconsult.core.errors import request_validation_handler, validation_handler

CANARY = "ZZ-PHI-CANARY-1234"
ALLOWED_ERROR_KEYS = {"loc", "type", "msg"}


class _FakeRequest:
    """Minimal stand-in; the handler must not read the request at all."""

    scope = {"type": "http", "path": "/api/session/init"}


class _SessionInitModel(BaseModel):
    """Mirrors the relevant part of ``SessionInitRequest``."""

    chief_complaint: str = ""
    conditions: list[str] = Field(default_factory=list)


class _QAPair(BaseModel):
    question: str
    answer: str


class _GeneratePdfModel(BaseModel):
    """Mirrors the relevant part of ``GeneratePdfRequest``."""

    session_id: str
    qa_pairs: list[_QAPair] = Field(..., min_length=1, max_length=5)


def _run(handler, exc):
    return asyncio.run(handler(_FakeRequest(), exc))


def _request_errors(model, payload) -> RequestValidationError:
    """Build the exception FastAPI would raise for an invalid JSON body."""
    try:
        model(**payload)
    except ValidationError as exc:
        raw_errors = exc.errors()
        # Precondition: prove the trap is real, so a pydantic change that
        # stopped emitting ``input`` cannot make the PHI assertions vacuous.
        assert any("input" in error for error in raw_errors)
        errors = [{**error, "loc": ("body", *error["loc"])} for error in raw_errors]
        return RequestValidationError(errors, body=payload)
    raise AssertionError("payload unexpectedly passed validation")


def _body(response) -> dict:
    return json.loads(response.body)


def test_session_init_shape_returns_stable_422_contract():
    exc = _request_errors(_SessionInitModel, {"conditions": "not_a_list"})
    response = _run(request_validation_handler, exc)

    assert response.status_code == 422
    body = _body(response)
    assert body["code"] == "validation_failed"
    assert isinstance(body["detail"], str) and body["detail"]
    assert isinstance(body["errors"], list) and body["errors"]
    for error in body["errors"]:
        assert set(error) == ALLOWED_ERROR_KEYS
        assert error["loc"][:2] == ["body", "conditions"]
        assert isinstance(error["type"], str) and error["type"]
        assert isinstance(error["msg"], str) and error["msg"]


def test_response_never_contains_input_or_ctx_or_the_submitted_value():
    exc = _request_errors(_SessionInitModel, {"conditions": CANARY})
    response = _run(request_validation_handler, exc)

    body = _body(response)
    for error in body["errors"]:
        assert "input" not in error
        assert "ctx" not in error
    # The raw body text must not echo the submitted value either.
    assert CANARY not in response.body.decode()


def test_explicit_ctx_payload_is_stripped_and_serializable():
    # Custom validators put the offending value/exception in ``ctx``; a
    # ``ValueError`` there is not even JSON-serializable, so stripping ctx is
    # also what keeps the response from blowing up into a 500.
    exc = RequestValidationError(
        [
            {
                "loc": ("body", "conditions", 0),
                "type": "value_error",
                "msg": "Value error, invalid condition",
                "input": CANARY,
                "ctx": {"error": ValueError(CANARY)},
            }
        ],
        body={"conditions": [CANARY]},
    )
    response = _run(request_validation_handler, exc)

    assert response.status_code == 422
    body = _body(response)
    assert body["code"] == "validation_failed"
    assert body["errors"] == [
        {
            "loc": ["body", "conditions", 0],
            "type": "value_error",
            "msg": "Value error, invalid condition",
        }
    ]
    assert CANARY not in response.body.decode()


def test_logs_are_phi_safe(caplog):
    exc = _request_errors(_SessionInitModel, {"conditions": CANARY})

    with caplog.at_level(logging.WARNING):
        response = _run(request_validation_handler, exc)

    assert response.status_code == 422
    assert CANARY not in caplog.text
    # PHI-safe logging still records the count and the loc paths.
    assert "Validacao rejeitada" in caplog.text
    assert "conditions" in caplog.text
    assert "1 erro(s)" in caplog.text


def test_generate_pdf_style_body_uses_the_same_code():
    exc = _request_errors(_GeneratePdfModel, {"session_id": "x", "qa_pairs": []})
    response = _run(request_validation_handler, exc)

    assert response.status_code == 422
    body = _body(response)
    assert body["code"] == "validation_failed"
    assert isinstance(body["detail"], str)
    assert body["errors"]
    for error in body["errors"]:
        assert set(error) == ALLOWED_ERROR_KEYS
        assert error["loc"][:2] == ["body", "qa_pairs"]
    assert CANARY not in response.body.decode()


@pytest.mark.parametrize(
    "payload", [{"conditions": "not_a_list"}, {"conditions": CANARY}]
)
def test_pydantic_validation_handler_stays_phi_safe(payload, caplog):
    """The pydantic-level handler keeps its code and is sanitized too."""
    try:
        _SessionInitModel(**payload)
    except ValidationError as exc:
        with caplog.at_level(logging.WARNING):
            response = _run(validation_handler, exc)
    else:  # pragma: no cover - payloads are invalid by construction
        raise AssertionError("payload unexpectedly passed validation")

    assert response.status_code == 422
    body = _body(response)
    assert body["code"] == "validation_failed"
    for error in body["errors"]:
        assert set(error) == ALLOWED_ERROR_KEYS
    assert CANARY not in response.body.decode()
    assert CANARY not in caplog.text
