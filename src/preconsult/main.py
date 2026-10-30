"""Entry point for the served ASGI app.

The app is built by ``preconsult.host`` (a Starlette app with the API, health,
crawler documents, legal pages and the SPA); this module exists so ASGI servers
can use the stable ``preconsult.main:app`` target, and so Sentry is initialised
once before the app is constructed.

There is no second frontend host and no state socket: the React SPA is served
from the same app at ``/``.
"""

import logging
import time

# Start the clock before the first import so the boot event measures the app
# import cost, not just the Sentry/host tail. Gunicorn logs "Booting worker"
# before this module runs, so this is the attribution point for a cold start.
_BOOT_STARTED = time.monotonic()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from preconsult.core.config import SENTRY_DSN  # noqa: E402
from preconsult.core.observability import log_event  # noqa: E402
from preconsult.core.sentry import init_sentry  # noqa: E402

if SENTRY_DSN:
    init_sentry(SENTRY_DSN)

from preconsult.host import app  # noqa: E402, F401

# Emitted once per worker, before uvicorn's "Application startup complete".
# duration_ms is the previously invisible import cost between gunicorn's
# "Booting worker" line and the first request; keep it PHI-free and metadata
# only, like every other structured event.
log_event(
    logging.INFO,
    "app.boot",
    duration_ms=round((time.monotonic() - _BOOT_STARTED) * 1000),
)
