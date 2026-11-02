"""Tiny warmer for the PreConsult Lambda.

Not a load test and not a health monitor: it performs one GET of the
dependency-free liveness route so a single execution environment stays warm
between real visitors. The EventBridge rule invokes it every five minutes.

Only the path and outcome are logged; no query string, headers or body.
"""

import os
import urllib.request

TARGET_URL = os.environ["TARGET_URL"].rstrip("/") + "/health/live"


def handler(event, context):
    request = urllib.request.Request(
        TARGET_URL,
        headers={"User-Agent": "preconsult-warmer/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.status
    except Exception as exc:  # noqa: BLE001 - report, never fail the schedule
        print(f"warmer: liveness probe failed: {type(exc).__name__}")
        return {"ok": False}

    print(f"warmer: liveness probe status={status}")
    return {"ok": 200 <= status < 300}
