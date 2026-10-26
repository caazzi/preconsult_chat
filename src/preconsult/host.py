"""The Reflex-free ASGI application.

Everything the site serves — the API, health probes, crawler documents, legal
pages and the SPA — assembled without importing Reflex. This is the app that
takes over ``/`` at cutover and the one the tests and browser E2E drive today,
so the switch is a deployment change rather than a rewrite.

Registration order is the contract (Starlette matches first-registered-wins):
``/api`` before the site routes, and the SPA mount **last** so it only sees
paths nothing else claimed. The middleware order is likewise deliberate:
``BotGateMiddleware`` outermost (a blocked scanner gets a fast 403 and is not
counted as a request outcome), then ``RequestIDMiddleware``, then GZip.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware

from preconsult.api.app import build_api_app
from preconsult.site.health import EventChannelProbe, register_health_routes
from preconsult.site.middleware import BotGateMiddleware
from preconsult.site.request_id import RequestIDMiddleware
from preconsult.site.routes import register_site_routes
from preconsult.site.static import SPAStaticFiles


def resolve_spa_dist() -> Path | None:
    """Locate the built SPA without depending on the container's WORKDIR.

    ``WEB_DIST_DIR`` wins. Otherwise the working directory and its parent are
    both checked, which covers every layout in play: ``/app`` (the post-cutover
    WORKDIR), ``/app/reflex_app`` (the current one) and the repo root in tests.
    """
    override = os.environ.get("WEB_DIST_DIR", "").strip()
    if override:
        return Path(override)
    cwd = Path.cwd()
    for candidate in (cwd / "web" / "dist", cwd.parent / "web" / "dist"):
        if candidate.is_dir():
            return candidate
    return None


def build_starlette_app(
    spa_dist: str | Path | None = None,
    event_channel_probe: EventChannelProbe | None = None,
) -> Starlette:
    """Build the inner Starlette app (routes + GZip), without the middlewares.

    Exposed separately so tests can inspect the route table and the middleware
    stack without unwrapping the ASGI middlewares.

    ``event_channel_probe`` is only meaningful while something still owns an
    interactive socket; leave it out and /health answers ``not_configured``.
    """
    app = Starlette()
    app.mount("/api", build_api_app())
    register_health_routes(app, event_channel_probe=event_channel_probe)
    register_site_routes(app)

    dist = Path(spa_dist) if spa_dist else resolve_spa_dist()
    if dist is not None and dist.is_dir():
        # Last, so /api, /health, /privacy, /terms, /robots.txt and friends are
        # matched before the catch-all. SPAStaticFiles keeps the contract the
        # platform depends on: the document is no-store, hashed assets are
        # immutable, an unknown *navigation* falls back to the shell and a
        # missing *file* stays a 404.
        app.mount("/", SPAStaticFiles(directory=str(dist), html=True), name="spa")
    else:
        # A missing bundle is a packaging error, not a routing preference. Fail
        # loudly in the logs (path only, PHI-free) instead of serving a root 404
        # that looks like a routing bug. /health keeps answering either way.
        logging.error(
            "SPA bundle not found (looked for WEB_DIST_DIR, ./web/dist, ../web/dist)"
        )

    app.add_middleware(GZipMiddleware, minimum_size=500)
    return app


def build_asgi_app(
    spa_dist: str | Path | None = None,
    event_channel_probe: EventChannelProbe | None = None,
):
    """Build the served ASGI app: BotGate -> RequestID -> Starlette/GZip."""
    return BotGateMiddleware(
        RequestIDMiddleware(
            build_starlette_app(
                spa_dist=spa_dist, event_channel_probe=event_channel_probe
            )
        )
    )


# Module-level instance for ASGI servers: ``preconsult.host:app``.
app = build_asgi_app()
