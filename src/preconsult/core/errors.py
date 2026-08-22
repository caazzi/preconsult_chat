import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from google.api_core.exceptions import GoogleAPIError


class RedisUnavailableError(Exception):
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


async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError):
    logging.error(f"LLM indisponivel: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Servico de IA temporariamente indisponivel. Tente novamente.",
            "code": "llm_unavailable",
        },
    )


async def validation_handler(request: Request, exc: ValidationError):
    logging.warning(f"Erro de validacao: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Dados invalidos enviados.",
            "code": "validation_failed",
            "errors": exc.errors(),
        },
    )


async def google_api_handler(request: Request, exc: GoogleAPIError):
    logging.error(f"Erro na API Google: {exc}")
    return JSONResponse(
        status_code=502,
        content={
            "detail": "Erro no servico de IA. Tente novamente.",
            "code": "ai_upstream_error",
        },
    )


async def generic_handler(request: Request, exc: Exception):
    logging.error(f"Erro nao tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ocorreu um erro inesperado. Tente novamente.",
            "code": "internal_error",
        },
    )
