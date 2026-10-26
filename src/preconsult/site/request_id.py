"""Request correlation and outcome counters (Reflex-free).

Same contract as the middleware that used to live in the Reflex host minus the
Engine.IO bits: every response carries ``x-request-id``, every request emits a
PHI-safe ``http.request`` log line (method + path only), outcomes are counted as
``http.status.<code>``, and a 404 under ``/assets`` is counted and logged as
``static.asset_404`` — the tell that a cached shell references chunks that no
longer exist.

The socket-specific branches (``socket.handshake_rejected`` and the stale-session
400 recovery) are deliberately absent: they exist only for the Engine.IO
transport and disappear with it.
"""

from __future__ import annotations

import logging

from preconsult.core.observability import _inc, log_event, new_request_id


class RequestIDMiddleware:
    """Stamp an X-Request-ID on every response and emit a PHI-safe request log.

    Only the request method and path are logged (no query string, headers or
    body) so nothing user-supplied is captured. The id correlates a request
    across Cloud Run logs and the structured backend events, and the status is
    counted so failures are alertable by outcome.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_request_id()
        scope["request_id"] = request_id
        path = scope.get("path", "")
        method = scope.get("method", "")
        safe_path = path if len(path) <= 200 else path[:200]
        log_event(
            logging.DEBUG,
            "http.request",
            request_id=request_id,
            method=method,
            path=safe_path,
        )

        status_holder = {}

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                status = message.get("status", 0)
                status_holder["status"] = status
                headers = message.get("headers", [])
                message["headers"] = [
                    *headers,
                    (b"x-request-id", request_id.encode("ascii")),
                ]
                # A 404 on a hashed asset means a stale document is being served:
                # the browser is asking for chunks the current build does not
                # have. Count it (PHI-free: path + status only) so the class of
                # breakage is visible in /health/metrics before a user reports it.
                if path.startswith("/assets") and status == 404:
                    _inc("static.asset_404")
                    log_event(
                        logging.WARNING,
                        "static.asset_404",
                        request_id=request_id,
                        path=safe_path,
                        status=status,
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            status = status_holder.get("status")
            if status is not None:
                _inc(f"http.status.{status}")
                # Surface non-2xx outcomes at INFO so failures are queryable by
                # path+status; 2xx stays at DEBUG to keep log volume modest.
                log_event(
                    logging.INFO if status >= 400 else logging.DEBUG,
                    "http.status",
                    request_id=request_id,
                    method=method,
                    path=safe_path,
                    status=status,
                )
