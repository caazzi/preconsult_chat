"""The ``/api`` FastAPI sub-app, built without Reflex.

Extracted from the Reflex host so the API surface survives the SPA cutover. The
host mounts the returned app at ``/api``; nothing here imports Reflex.

Handler registration order is part of the contract: the ``Exception`` handler
must be added last, and ``RequestValidationError`` must override FastAPI's
default so oversized/invalid bodies return the stable ``validation_failed`` code
without echoing submitted values.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from preconsult.api.endpoints import public_router, router
from preconsult.core.errors import (
    LLMUnavailableError,
    LLMUpstreamError,
    RedisQuotaExceededError,
    RedisUnavailableError,
    generic_handler,
    http_exception_handler,
    llm_unavailable_handler,
    llm_upstream_handler,
    redis_quota_exceeded_handler,
    redis_unavailable_handler,
    request_validation_handler,
    validation_handler,
)

DESCRIPTION = (
    "Privacy-first medical intake assistant. Ephemeral sessions (30-min TTL), "
    "no persistence of health data. Interactive schema auto-generated from the "
    "FastAPI routes; behavioral contracts (SSE framing, session TTL, rate limits) "
    "are documented in docs/api-contract.md."
)

OPENAPI_TAGS = [
    {
        "name": "Session Lifecycle",
        "description": "Create and manage ephemeral patient sessions.",
    },
    {
        "name": "Clinical Question Streams",
        "description": "SSE streams of LLM-generated clinical questions.",
    },
    {
        "name": "PDF Report",
        "description": "Deterministic in-memory PDF generation.",
    },
    {
        "name": "Analytics",
        "description": "Anonymous funnel analytics.",
    },
]


def build_api_app() -> FastAPI:
    """Build the authenticated API sub-app (mount it at ``/api``)."""
    api = FastAPI(
        title="PreConsult API",
        version="1.0.0",
        description=DESCRIPTION,
        contact={"name": "PreConsult", "url": "https://pre-consult.org"},
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    api.add_exception_handler(RedisUnavailableError, redis_unavailable_handler)
    api.add_exception_handler(RedisQuotaExceededError, redis_quota_exceeded_handler)
    api.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
    api.add_exception_handler(HTTPException, http_exception_handler)
    api.add_exception_handler(ValidationError, validation_handler)
    # FastAPI raises RequestValidationError (not pydantic ValidationError) for
    # request-body failures; without this the stable `validation_failed` code
    # never reached 422 responses. Handler strips submitted values (PHI).
    api.add_exception_handler(RequestValidationError, request_validation_handler)
    # Providers translate their own vendor exceptions into LLMUpstreamError, so
    # one handler covers every family and a new provider needs no change here.
    api.add_exception_handler(LLMUpstreamError, llm_upstream_handler)
    api.add_exception_handler(Exception, generic_handler)
    api.include_router(router)
    api.include_router(public_router)
    return api
