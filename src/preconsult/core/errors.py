import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from google.api_core.exceptions import GoogleAPIError


class RedisUnavailableError(Exception):
    pass


class LLMUnavailableError(Exception):
    pass


async def redis_unavailable_handler(request: Request, exc: RedisUnavailableError):
    logging.error(f"Redis indisponivel: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Servico temporariamente indisponivel. Tente novamente em instantes."},
    )


async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError):
    logging.error(f"LLM indisponivel: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Servico de IA temporariamente indisponivel. Tente novamente."},
    )


async def validation_handler(request: Request, exc: ValidationError):
    logging.warning(f"Erro de validacao: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Dados invalidos enviados.", "errors": exc.errors()},
    )


async def google_api_handler(request: Request, exc: GoogleAPIError):
    logging.error(f"Erro na API Google: {exc}")
    return JSONResponse(
        status_code=502,
        content={"detail": "Erro no servico de IA. Tente novamente."},
    )


async def generic_handler(request: Request, exc: Exception):
    logging.error(f"Erro nao tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocorreu um erro inesperado. Tente novamente."},
    )
