"""ASGI middleware that is not tied to Reflex.

``BotGateMiddleware`` protects the Redis-backed API paths from scanner traffic.
It lived in the Reflex host only because that is where the app was assembled;
it has no Reflex dependency and must survive the cutover unchanged.

The socket-coupled pair (``_RequestIDMiddleware`` and
``_StaleSocketSessionMiddleware``) deliberately stays in the host: one of them
counts ``/_event`` recoveries and the other performs them, so they move or die
together when Engine.IO is removed.
"""

from __future__ import annotations

import hashlib
import json
import logging

from preconsult.core.observability import log_event, new_request_id


class BotGateMiddleware:
    """Block obvious scanners/bots BEFORE they reach Redis-touching endpoints.

    With serverless Redis on a free tier, a scanner burst against /_event,
    /api/session/init or /api/analytics/event can exhaust the request quota that
    real users need. This is a lightweight, conservative gate: it only matches a
    small set of unambiguous CLI/bot user-agents on the Redis-backed paths and
    returns a fast 403 without touching storage. Browser traffic passes through
    untouched (permissive by design); Cloudflare WAF/Bot Shield can be stricter.
    """

    # Only these paths may trigger Redis (sessions, rate-limit, analytics).
    _REDIS_PATHS = (
        "/api/session/init",
        "/api/interview-questions-stream",
        "/api/initial-questions-stream",
        "/api/generate-pdf",
        "/api/analytics/event",
    )
    # Case-insensitive substrings that identify unambiguous non-browser clients.
    _BOT_UA_FRAGMENTS = (
        "curl",
        "wget",
        "python-requests",
        "python-urllib",
        "go-http-client",
        "node-fetch",
        "php/",
        "java/",
        "axios",
        "okhttp",
        "libwww-perl",
        "scrapy",
        "headlesschrome",
        "phantomjs",
        "screaming frog",
        "ahrefsbot",
        "semrushbot",
        "mj12bot",
        "dotbot",
        "bytespider",
        "petalbot",
        "awario",
        "pycurl",
    )

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not any(path.startswith(p) for p in self._REDIS_PATHS):
            await self.app(scope, receive, send)
            return

        user_agent = ""
        for name, value in scope.get("headers", []):
            if name == b"user-agent":
                user_agent = value.decode("latin-1", "replace")
                break

        if user_agent and any(
            frag in user_agent.lower() for frag in self._BOT_UA_FRAGMENTS
        ):
            # PHI-safe: log a hash of the UA, never the raw value.
            ua_hash = hashlib.sha256(user_agent.encode("utf-8", "replace")).hexdigest()[
                :16
            ]
            log_event(
                logging.INFO,
                "gate.blocked",
                request_id=new_request_id(),
                path=path[:200],
                ua_hash=ua_hash,
            )
            body = json.dumps({"detail": "Forbidden", "code": "bot_blocked"}).encode(
                "utf-8"
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
