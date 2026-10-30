"""Regression tests for the served entrypoint (``preconsult.main``).

The entrypoint only initialises Sentry and re-exports ``preconsult.host.app`` so
ASGI servers have a stable target. It used to re-export the Reflex host; that
host no longer exists.
"""

import importlib
import logging
import os
import re
from unittest.mock import patch

from preconsult.core.sentry import init_sentry


def test_main_entrypoint_exports_the_host_app():
    assert not os.environ.get("SENTRY_DSN"), "test env must not carry a real DSN"

    main = importlib.import_module("preconsult.main")
    host = importlib.import_module("preconsult.host")

    assert main.app is host.app


def test_main_entrypoint_logs_boot_duration(caplog):
    with caplog.at_level(logging.INFO):
        importlib.reload(importlib.import_module("preconsult.main"))

    boot_lines = [
        record.getMessage()
        for record in caplog.records
        if "event=app.boot" in record.getMessage()
    ]

    assert boot_lines, "the entrypoint must log how long the app import took"
    assert re.search(r"duration_ms=\d+", boot_lines[0])


def test_init_sentry_locks_down_phi_capture():
    with patch("sentry_sdk.init") as mock_init:
        init_sentry("https://k@example.invalid/1")

    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs

    assert kwargs["dsn"] == "https://k@example.invalid/1"
    assert kwargs["send_default_pii"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["include_local_variables"] is False
    assert kwargs["traces_sample_rate"] == 0.05

    integration_names = {type(i).__name__ for i in kwargs["integrations"]}
    assert integration_names == {"FastApiIntegration", "LoggingIntegration"}
    log_integration = next(
        i for i in kwargs["integrations"] if type(i).__name__ == "LoggingIntegration"
    )
    # Breadcrumb handler honours `level`, event handler honours `event_level`.
    assert log_integration._breadcrumb_handler.level == logging.INFO
    assert log_integration._handler.level == logging.ERROR
