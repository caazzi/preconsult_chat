import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from fastapi import FastAPI
from pydantic import ValidationError
from google.api_core.exceptions import GoogleAPIError
from preconsult.api.endpoints import router as api_router
from preconsult.core.config import SENTRY_DSN
from preconsult.services.session_service import get_redis, _redis_available
from preconsult.core.errors import (
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
        traces_sample_rate=0.1,
    )
    logging.info("Sentry SDK inicializado.")

app = FastAPI(
    title="PreConsult API",
    description="An API to help patients prepare for their doctor's visit.",
    version="1.0.0"
)

app.add_exception_handler(RedisUnavailableError, redis_unavailable_handler)
app.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
app.add_exception_handler(ValidationError, validation_handler)
app.add_exception_handler(GoogleAPIError, google_api_handler)
app.add_exception_handler(Exception, generic_handler)

app.include_router(api_router, prefix="/api", tags=["Medical Chat"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the PreConsult API. Go to /docs for the API documentation."}


@app.get("/health", tags=["Health"])
async def health():
    redis_status = "ok" if _redis_available is not False else "unavailable"
    return {"status": "healthy", "redis": redis_status}
