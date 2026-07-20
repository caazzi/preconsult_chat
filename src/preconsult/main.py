"""
Re-exports the Reflex ASGI app for development convenience.

In production, the app is served via `reflex_app.preconsult.preconsult:api`.
This module exists so that `uvicorn preconsult.main:app` works locally.
"""
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from pydantic import ValidationError  # noqa: E402
from google.api_core.exceptions import GoogleAPIError  # noqa: E402
from preconsult.core.config import SENTRY_DSN  # noqa: E402
from preconsult.core.errors import (  # noqa: E402
    RedisUnavailableError,
    LLMUnavailableError,
    redis_unavailable_handler,
    llm_unavailable_handler,
    validation_handler,
    google_api_handler,
    generic_handler,
)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.01,
    )
    logging.info("Sentry SDK inicializado.")

from reflex_app.preconsult.preconsult import api as app  # noqa: E402

app.add_exception_handler(RedisUnavailableError, redis_unavailable_handler)
app.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
app.add_exception_handler(ValidationError, validation_handler)
app.add_exception_handler(GoogleAPIError, google_api_handler)
app.add_exception_handler(Exception, generic_handler)
