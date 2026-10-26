"""Static-file mounts for the served frontends.

``SPAStaticFiles`` is the SPA mount and survives the cutover unchanged: the
React app needs the same contract either way — real files are immutable and
content-hashed, the shell is ``no-store``, an unknown navigation falls back to
``index.html``, and a missing *file* stays a 404.

It is Reflex-free; the host imports it for the ``/next`` mount today and will
mount it at ``/`` after the cutover.
"""

from __future__ import annotations

from starlette.responses import Response
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    _IMMUTABLE = "public, max-age=31536000, immutable"
    _NO_STORE = "no-store, no-cache, must-revalidate"

    async def get_response(self, path: str, scope) -> Response:
        # Starlette normalizes the mount root to ".", so a bare "." check on
        # the last segment would misclassify the document as a file and pin it
        # immutable for a year (the stale-shell hazard). Only real files are
        # immutable; the shell is always no-store.
        is_document = path in (".", "index.html")
        is_file = not is_document and (
            path.startswith("assets/")
            or "/assets/" in path
            or "." in path.rsplit("/", 1)[-1]
        )
        try:
            response = await super().get_response(path, scope)
        except Exception as exc:
            # StaticFiles raises HTTPException(404) for a missing path. Only an
            # unknown *navigation* route may fall back to the app shell; a
            # missing file must stay a 404. Serving HTML for a missing hashed
            # asset -- and caching it immutable -- is how a broken deploy turns
            # into "Unexpected token '<'" and a poisoned browser/CDN cache.
            if getattr(exc, "status_code", None) != 404 or is_file:
                raise
            response = await super().get_response("index.html", scope)
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
