import logging
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from botocore.exceptions import ClientError
from google.api_core.exceptions import GoogleAPIError


class RedisUnavailableError(Exception):
    pass


class RedisQuotaExceededError(Exception):
    """Raised when the upstream Redis (Upstash) request quota is exhausted.

    Distinct from :class:`RedisUnavailableError` so clients/ops can tell a
    deliberate, recoverable quota exhaustion (daily resets) apart from a general
    outage, and can alert on it specifically.
    """
    pass


class LLMUnavailableError(Exception):
    pass


# Stable, machine-readable code per HTTP status for the generic errors raised
# as HTTPException throughout the API. Clients can alert on these without
# parsing localized detail text.
HTTP_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "auth_failed",
    404: "session_expired",
    422: "validation_failed",
    429: "rate_limited",
    500: "internal_error",
    502: "ai_upstream_error",
    503: "service_unavailable",
}


async def http_exception_handler(request: Request, exc: HTTPException):
    """Rewrite HTTPException to carry a stable machine-readable ``code``.

    The original ``detail`` is preserved (still a string) so existing clients
    and the smoke tests keep working, with ``code`` added as a sibling field.
    """
    detail = exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": detail,
            "code": HTTP_STATUS_CODES.get(exc.status_code, "unknown"),
            "headers": exc.headers,
        } if detail else {
            "code": HTTP_STATUS_CODES.get(exc.status_code, "unknown"),
        },
    )


async def redis_unavailable_handler(request: Request, exc: RedisUnavailableError):
    logging.error(f"Redis indisponivel: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Servico temporariamente indisponivel. Tente novamente em instantes.",
            "code": "redis_unavailable",
        },
    )


async def redis_quota_exceeded_handler(request: Request, exc: RedisQuotaExceededError):
    logging.error(f"Redis quota excedida: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Servico temporariamente indisponivel. A fila de dados esta cheia; tente novamente mais tarde.",
            "code": "redis_quota_exceeded",
        },
    )


async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError):
    logging.error(f"LLM indisponivel: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Servico de IA temporariamente indisponivel. Tente novamente.",
            "code": "llm_unavailable",
        },
    )


def _sanitize_validation_errors(exc) -> list[dict]:
    """Reduce validation errors to PHI-free fields.

    Both pydantic's ``ValidationError`` and FastAPI's
    ``RequestValidationError`` report an ``input`` key holding the submitted
    value (which can be a chief complaint) plus a ``ctx`` key that often holds
    the raw value/exception. Neither may be echoed back or logged, so only
    ``loc``, ``type`` and ``msg`` survive.
    """
    safe: list[dict] = []
    for err in exc.errors():
        if isinstance(err, dict):
            loc = err.get("loc") or ()
            err_type = err.get("type")
            msg = err.get("msg")
        else:  # defensive: tolerate non-dict error details
            loc = getattr(err, "loc", ()) or ()
            err_type = getattr(err, "type", None)
            msg = getattr(err, "msg", None)
        try:
            loc_list = list(loc)
        except TypeError:
            loc_list = []
        safe.append(
            {
                "loc": loc_list,
                "type": str(err_type) if err_type is not None else "",
                "msg": str(msg) if msg is not None else "",
            }
        )
    return safe


def _log_validation_rejection(exc) -> list[dict]:
    """Log a validation rejection without any content or raw values.

    Only the number of errors and their ``loc`` paths (field names/indices)
    are emitted; the exception string embeds ``input`` values and must never be
    interpolated.
    """
    errors = _sanitize_validation_errors(exc)
    logging.warning(
        "Validacao rejeitada: %d erro(s) campos=%s",
        len(errors),
        [error["loc"] for error in errors],
    )
    return errors


async def request_validation_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request-body validation failures (the real 422 path).

    FastAPI raises ``RequestValidationError`` around the body's pydantic
    ``ValidationError``, so the ``ValidationError`` handler below never sees
    request-body failures. This handler keeps the stable ``validation_failed``
    code and strips the submitted values from the response and the logs.
    """
    errors = _log_validation_rejection(exc)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Dados invalidos enviados.",
            "code": "validation_failed",
            "errors": errors,
        },
    )


async def validation_handler(request: Request, exc: ValidationError):
    errors = _log_validation_rejection(exc)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Dados invalidos enviados.",
            "code": "validation_failed",
            "errors": errors,
        },
    )


async def bedrock_api_handler(request: Request, exc: Exception):
    """Map a Bedrock/Anthropic upstream failure to a stable 502/503 code.

    Throttling is a retriable upstream condition (503 ``llm_unavailable``);
    every other Bedrock client/protocol error is an upstream failure (502
    ``ai_upstream_error``). The response stays generic and never leaks the
    exception message, which can embed request details.
    """
    throttled = _is_bedrock_throttling(exc)
    logging.error("Bedrock upstream error (throttled=%s): %s", throttled, exc)
    if throttled:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Servico de IA temporariamente indisponivel. Tente novamente.",
                "code": "llm_unavailable",
            },
        )
    return JSONResponse(
        status_code=502,
        content={
            "detail": "Erro no servico de IA. Tente novamente.",
            "code": "ai_upstream_error",
        },
    )


def _is_bedrock_throttling(exc: Exception) -> bool:
    """Whether a Bedrock error is a retriable throttling/quota condition."""
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        return code in (
            "ThrottlingException",
            "Throttling",
            "TooManyRequestsException",
            "ServiceQuotaExceededException",
        )
    message = str(exc).lower()
    return "throttl" in message or "too many requests" in message


async def google_api_handler(request: Request, exc: GoogleAPIError):
    """Map a Vertex/Gemini upstream failure to the stable 502/503 code.

    Vertex throttling is retriable (503 ``llm_unavailable``); everything else is
    an upstream failure (502 ``ai_upstream_error``). The response stays generic
    and never echoes the exception, which can embed request details.
    """
    throttled = _is_google_throttling(exc)
    logging.error("Vertex upstream error (throttled=%s): %s", throttled, exc)
    if throttled:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Servico de IA temporariamente indisponivel. Tente novamente.",
                "code": "llm_unavailable",
            },
        )
    return JSONResponse(
        status_code=502,
        content={
            "detail": "Erro ao processar a solicitacao com a IA.",
            "code": "ai_upstream_error",
        },
    )


def _is_google_throttling(exc: Exception) -> bool:
    """Whether a Vertex/Gemini error is a retriable throttling/quota condition."""
    try:
        from google.api_core import exceptions as google_exceptions
    except ImportError:  # pragma: no cover - google deps are a hard dependency
        google_exceptions = None

    if google_exceptions is not None and isinstance(
        exc, (google_exceptions.ResourceExhausted, google_exceptions.TooManyRequests)
    ):
        return True
    message = str(exc).lower()
    return "429" in message or "resource exhausted" in message or "quota" in message


async def generic_handler(request: Request, exc: Exception):
    logging.error(f"Erro nao tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ocorreu um erro inesperado. Tente novamente.",
            "code": "internal_error",
        },
    )
