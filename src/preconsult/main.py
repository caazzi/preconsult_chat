import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import os
from fastapi import FastAPI
from preconsult.api.endpoints import router as api_router
from preconsult.core.config import SENTRY_DSN

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

app.include_router(api_router, prefix="/api", tags=["Medical Chat"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the PreConsult API. Go to /docs for the API documentation."}
