"""Static-file mounts for the served frontends.

``SPAStaticFiles`` is the SPA mount and survives the cutover unchanged: the
React app needs the same contract either way — real files are immutable and
content-hashed, the shell is ``no-store``, an unknown navigation falls back to
``index.html``, and a missing *file* stays a 404.

Because the mount moves to ``/`` it inherits the whole origin's 404 semantics:
every path the router does not know lands here, so scanner probes (``.php``,
``wp-admin``, ``.env``, …) and Reflex backend prefixes (``/_event``, …) are
answered explicitly instead of being handed the SPA shell — that is why the
guards below live in this module rather than in the old Reflex host.

The shell fallback is **navigation-only**: a request must accept HTML, which
keeps a canary probe (``Accept: */*``) from turning an arbitrary path into a
200. Non-HTTP scopes are rejected before ``StaticFiles``' HTTP-only assertion,
because a stale ``/_event`` WebSocket retry used to surface as a 500 traceback.

It is Reflex-free; the host imports it for the ``/next`` mount today and will
mount it at ``/`` after the cutover.
"""

from __future__ import annotations

import logging
import os
from urllib.parse import parse_qs

from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from preconsult.core.observability import log_event, new_request_id


class SPAStaticFiles(StaticFiles):
    _IMMUTABLE = "public, max-age=31536000, immutable"
    _NO_STORE = "no-store, no-cache, must-revalidate"

    # Reflex backend endpoints must never be answered by the SPA fallback. A
    # backend path reaching the shell means the state socket got HTML instead
    # of a handshake (it then silently drops events), so answer with a clear
    # 404 text response and make the regression visible in the logs.
    _BACKEND_PREFIXES = (
        "_event",
        "_ping",
        "_health",
        "_upload",
        "auth-codespace",
        "_all_routes",
    )

    # Paths that are never client-side routes. A scanner appends canaries to
    # these (``/.git/zzcanary-...``) to detect a catch-all 200; the shell must
    # not answer them even when the client claims to accept HTML.
    _SCANNER_PREFIXES = (
        ".ssh",
        ".git",
        ".svn",
        ".hg",
        ".aws",
        ".docker",
        ".vscode",
        "actuator",
        "wp-json",
        "cgi-bin",
        "server-status",
        "server-info",
    )

    # Prerendered per-language documents (see web/scripts/prerender.mjs). Both
    # are documents, never immutable assets; the Portuguese one is selected by
    # the `?lang=` the SPA mirrors into the URL (there is no cookie).
    _PT_DOCUMENT = "index.pt.html"

    def _document_for(self, scope) -> str:
        """The prerendered document matching the request's language.

        `/?lang=pt` is the crawler/`hreflang` URL for Portuguese, so it must be
        answered with Portuguese HTML rather than the English shell. A build
        without the pt variant (test fixtures, a partial deploy) falls back to
        English instead of 404ing the landing.
        """
        if self._wants_portuguese(scope) and os.path.isfile(
            os.path.join(os.fspath(self.directory), self._PT_DOCUMENT)
        ):
            return self._PT_DOCUMENT
        return "index.html"

    @staticmethod
    def _wants_portuguese(scope) -> bool:
        raw = scope.get("query_string") or b""
        if not isinstance(raw, (bytes, bytearray)):
            return False
        try:
            query = parse_qs(bytes(raw).decode("latin-1"))
        except (UnicodeDecodeError, AttributeError):  # pragma: no cover - defensive
            return False
        return query.get("lang") == ["pt"]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # This mount is the root catch-all, so it also sees WebSocket
            # upgrades (a stale Reflex client retrying /_event). StaticFiles
            # asserts scope["type"] == "http"; close the handshake cleanly
            # instead of turning every retry into a 500 + traceback.
            if scope["type"] == "websocket":
                log_event(
                    logging.WARNING,
                    "static.non_http_rejected",
                    request_id=new_request_id(),
                    path=str(scope.get("path", ""))[:200],
                    scope_type="websocket",
                )
                await send({"type": "websocket.close", "code": 1008})
            return
        await super().__call__(scope, receive, send)

    @staticmethod
    def _accepts_html(scope) -> bool:
        """Whether the client is asking for a document, not a file/probe.

        Browser navigations send ``Accept: text/html,...``; scanners and CLI
        clients send ``*/*`` or omit it. Only the former may receive the SPA
        shell, so a canary probe to a random path cannot turn into a 200.
        """
        for name, value in scope.get("headers", []):
            if name.lower() != b"accept":
                continue
            accept = value.decode("latin-1").lower()
            if "text/html" in accept or "application/xhtml+xml" in accept:
                return True
        return False

    async def get_response(self, path: str, scope) -> Response:
        path_lower = path.lower()

        # Scanner probes are never app routes. Answer them with a cheap plain
        # 404 before touching the filesystem or the shell fallback.
        if (
            any(
                path_lower.endswith(ext)
                for ext in (".php", ".asp", ".aspx", ".jsp", ".cgi")
            )
            or (
                "wp-admin" in path_lower
                or "wp-content" in path_lower
                or ".env" in path_lower
                or "phpmyadmin" in path_lower
            )
            or any(
                path_lower == prefix or path_lower.startswith(prefix + "/")
                for prefix in self._SCANNER_PREFIXES
            )
        ):
            return Response("Not Found", status_code=404, media_type="text/plain")

        if any(
            path_lower == prefix or path_lower.startswith(prefix + "/")
            for prefix in self._BACKEND_PREFIXES
        ):
            # Metadata only: the normalized path (never the query string or
            # any user content), so the zero-PHI guarantee holds.
            log_event(
                logging.WARNING,
                "static.backend_prefix_404",
                request_id=new_request_id(),
                path=path_lower,
            )
            return Response("Not Found", status_code=404, media_type="text/plain")

        # Starlette normalizes the mount root to ".", so a bare "." check on
        # the last segment would misclassify the document as a file and pin it
        # immutable for a year (the stale-shell hazard). Only real files are
        # immutable; the shell is always no-store.
        is_document = path in (".", "index.html", self._PT_DOCUMENT)
        is_file = not is_document and (
            path.startswith("assets/")
            or "/assets/" in path
            or "." in path.rsplit("/", 1)[-1]
        )
        # The mount root resolves to the prerendered document for this
        # language; an explicit file request keeps its own path.
        target = self._document_for(scope) if path == "." else path
        try:
            response = await super().get_response(target, scope)
        except Exception as exc:
            # StaticFiles raises HTTPException(404) for a missing path. Only an
            # unknown *navigation* route may fall back to the app shell; a
            # missing file must stay a 404. Serving HTML for a missing hashed
            # asset -- and caching it immutable -- is how a broken deploy turns
            # into "Unexpected token '<'" and a poisoned browser/CDN cache.
            if getattr(exc, "status_code", None) != 404 or is_file:
                raise
            # Only a real navigation may fall back to the shell. A scanner,
            # canary probe or CLI client asking for a random path does not
            # accept HTML, so answer with the same plain 404 as the guards
            # above instead of a 200 shell.
            if not self._accepts_html(scope):
                return Response("Not Found", status_code=404, media_type="text/plain")
            response = await super().get_response(self._document_for(scope), scope)
            self._apply_cache_headers(response, immutable=False)
            return response
        self._apply_cache_headers(response, immutable=is_file)
        return response

    @staticmethod
    def _apply_cache_headers(response: Response, *, immutable: bool) -> None:
        if immutable:
            response.headers["Cache-Control"] = SPAStaticFiles._IMMUTABLE
        else:
            response.headers["Cache-Control"] = SPAStaticFiles._NO_STORE
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        response.headers["Vary"] = "Accept-Encoding"
