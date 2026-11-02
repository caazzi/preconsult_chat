"""Regression tests for the served entrypoint (``preconsult.main``).

The entrypoint re-exports ``preconsult.host.app`` so ASGI servers have a stable
target and logs the import cost. It used to re-export the Reflex host; that host
no longer exists.
"""

import importlib
import logging
import re


def test_main_entrypoint_exports_the_host_app():
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
