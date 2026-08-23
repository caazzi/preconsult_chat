"""
Re-exports the Reflex ASGI app for development convenience.

In production, the app is served via `reflex_app.preconsult.preconsult:api`.
This module exists so that `uvicorn preconsult.main:app` works locally.
"""
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from google.api_core.exceptions import GoogleAPIError  # noqa: E402
from preconsult.core.config import SENTRY_DSN  # noqa: E402
from preconsult.core.errors import (  # noqa: E402
    RedisUnavailableError,
    RedisQuotaExceededError,
    LLMUnavailableError,
    http_exception_handler,
    redis_unavailable_handler,
    redis_quota_exceeded_handler,
    llm_unavailable_handler,
    validation_handler,
    google_api_handler,
    generic_handler,
)

if SENTRY_DSN:
    import os
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.05,
        # PreConsult handles health data; never let PII/PHI auto-attach to events.
        send_default_pii=False,
        # Enrich events with deploy context for routing/alerts.
        environment=os.environ.get("ENV", "production"),
        release=os.environ.get(
            "GIT_SHA", os.environ.get("K_REVISION", "dev")
        ),
    )
    logging.info("Sentry SDK inicializado.")

from reflex_app.preconsult.preconsult import api as app  # noqa: E402

app.add_exception_handler(RedisUnavailableError, redis_unavailable_handler)
app.add_exception_handler(RedisQuotaExceededError, redis_quota_exceeded_handler)
app.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ValidationError, validation_handler)
app.add_exception_handler(GoogleAPIError, google_api_handler)
app.add_exception_handler(Exception, generic_handler)
