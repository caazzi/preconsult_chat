"""Sentry SDK initialisation with PHI-safe defaults.

PreConsult handles health data, so telemetry must never capture user content.
The SDK defaults are unsafe for us (``max_request_body_size="medium"`` attaches
request bodies, ``include_local_variables=True`` attaches stack-frame locals),
and ``send_default_pii=False`` does not cover either of them -- both are locked
down explicitly below.

NOTE: this module is wired into the served entrypoint (``preconsult.main``) and
initialises only when ``SENTRY_DSN`` is set; production does not set it today.
"""

import logging
import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def init_sentry(dsn: str) -> None:
    """Initialise the Sentry SDK for the given DSN."""
    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.05,
        # PreConsult handles health data; never let PII/PHI auto-attach to events.
        send_default_pii=False,
        # Request bodies (chief complaint, answers) and stack locals can both
        # carry PHI, so opt out of capturing them entirely.
        max_request_body_size="never",
        include_local_variables=False,
        # Enrich events with deploy context for routing/alerts.
        environment=os.environ.get("ENV", "production"),
        release=os.environ.get("GIT_SHA", os.environ.get("K_REVISION", "dev")),
    )
    logging.info("Sentry SDK inicializado.")
