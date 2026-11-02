"""Regression tests for the served entrypoint (``preconsult.main``).

The entrypoint re-exports ``preconsult.host.app`` so ASGI servers have a stable
target and logs the import cost. It used to re-export the Reflex host; that host
no longer exists.
"""

import importlib
import json
import logging


def test_main_entrypoint_exports_the_host_app():
    main = importlib.import_module("preconsult.main")
    host = importlib.import_module("preconsult.host")

    assert main.app is host.app


def test_main_entrypoint_logs_boot_duration(caplog):
    with caplog.at_level(logging.INFO):
        importlib.reload(importlib.import_module("preconsult.main"))

    boot_lines = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]

    boot_events = [event for event in boot_lines if event["body"] == "app.boot"]
    assert boot_events, "the entrypoint must log how long the app import took"
    duration_ms = boot_events[0]["attributes"]["duration_ms"]
    assert isinstance(duration_ms, int)
    assert duration_ms >= 0
