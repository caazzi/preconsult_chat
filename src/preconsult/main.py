"""
Re-exports the Reflex ASGI app for development convenience.

In production, the app is served via `reflex_app.preconsult.preconsult:api`.
This module exists so that `uvicorn preconsult.main:app` works locally.

Exception handlers are already registered on the mounted FastAPI sub-app inside
`reflex_app.preconsult.preconsult`, so this entrypoint only re-exports it.
"""

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from preconsult.core.config import SENTRY_DSN  # noqa: E402
from preconsult.core.sentry import init_sentry  # noqa: E402

if SENTRY_DSN:
    init_sentry(SENTRY_DSN)

# Re-exported as the ASGI app: `uvicorn preconsult.main:app`.
from reflex_app.preconsult.preconsult import api as app  # noqa: E402, F401
