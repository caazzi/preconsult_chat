"""Regression tests for the local dev entrypoint (``preconsult.main``).

``main.py`` used to import ``_BotGateMiddleware`` and then call
``app.add_exception_handler(...)`` on it, which raised ``AttributeError`` at
import time -- so ``uvicorn preconsult.main:app`` could never boot. The
handlers already live on the FastAPI sub-app mounted by
``reflex_app.preconsult.preconsult``; the entrypoint must only re-export it.
"""

import importlib
import logging
import os
from unittest.mock import patch

from preconsult.core.sentry import init_sentry


def test_main_entrypoint_imports_and_exports_reflex_api():
    assert not os.environ.get("SENTRY_DSN"), "test env must not carry a real DSN"

    main = importlib.import_module("preconsult.main")
    reflex_app = importlib.import_module("reflex_app.preconsult.preconsult")

    assert main.app is reflex_app.api


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
