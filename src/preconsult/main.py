"""Entry point for the served ASGI app.

The app is built by ``preconsult.host`` (a Starlette app with the API, health,
crawler documents, legal pages and the SPA); this module exists so ASGI servers
can use the stable ``preconsult.main:app`` target, and so Sentry is initialised
once before the app is constructed.

There is no second frontend host and no state socket: the React SPA is served
from the same app at ``/``.
"""

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from preconsult.core.config import SENTRY_DSN  # noqa: E402
from preconsult.core.sentry import init_sentry  # noqa: E402

if SENTRY_DSN:
    init_sentry(SENTRY_DSN)

from preconsult.host import app  # noqa: E402, F401
