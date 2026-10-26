"""Static legal pages, served by the backend without Reflex.

The privacy/terms documents are plain HTML files under ``web/legal``. Keeping
them as files (not Python string literals) means they can be prerendered into
the SPA bundle later, and it keeps ~300 lines of inline markup out of the
frontend host module.

Nothing here depends on Reflex: the migration target is a plain FastAPI app
that serves the same documents at the same URLs.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

LEGAL_PAGES = ("privacy", "terms")
LEGAL_LANGUAGES = ("en", "pt")
DEFAULT_LANG = "en"

LANG_COOKIE = "preconsult_lang"


def _candidate_dirs() -> list[Path]:
    """Places ``web/legal`` may live, most specific first.

    ``LEGAL_DIR`` wins so a deployment (or a test) can point at an explicit
    directory. The remaining candidates cover the three ways this module is
    imported: from the source tree, from an installed wheel in ``.venv``
    (while the process runs at the repo root), and inside the container where
    the code lives at ``/app/src`` and the process runs from
    ``/app/reflex_app``.
    """
    candidates: list[Path] = []
    override = os.environ.get("LEGAL_DIR", "").strip()
    if override:
        candidates.append(Path(override))

    here = Path(__file__).resolve()
    candidates.extend(parent / "web" / "legal" for parent in here.parents[:4])

    cwd = Path.cwd()
    candidates.append(cwd / "web" / "legal")
    candidates.extend(parent / "web" / "legal" for parent in cwd.parents[:2])

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def legal_dir() -> Path:
    """Return the directory holding ``<page>.<lang>.html``.

    Raises ``FileNotFoundError`` when the documents are missing: that is a
    packaging error, not a request error, and should fail loudly rather than
    render an empty page.
    """
    for candidate in _candidate_dirs():
        if all(
            (candidate / f"{page}.{DEFAULT_LANG}.html").is_file()
            for page in LEGAL_PAGES
        ):
            return candidate
    searched = "\n  ".join(str(path) for path in _candidate_dirs())
    raise FileNotFoundError(f"legal pages not found; searched:\n  {searched}")


def resolve_lang(query_lang: str | None, cookie_lang: str | None) -> str:
    """Pick the document language the same way the Reflex pages did.

    Explicit ``?lang=`` wins, then the ``preconsult_lang`` cookie, then
    English. Any ``pt*`` value selects Portuguese.
    """
    raw = query_lang or cookie_lang or DEFAULT_LANG
    return "pt" if raw.lower().startswith("pt") else "en"


@lru_cache(maxsize=16)
def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def legal_html(page: str, lang: str) -> str:
    """Return the HTML document for ``page`` in ``lang``."""
    if page not in LEGAL_PAGES:
        raise ValueError(f"unknown legal page: {page}")
    if lang not in LEGAL_LANGUAGES:
        raise ValueError(f"unsupported legal language: {lang}")
    return _read(str(legal_dir() / f"{page}.{lang}.html"))


def legal_page_endpoint(page: str):
    """Build the FastAPI route handler for one legal page."""
    from starlette.responses import HTMLResponse

    async def endpoint(request):
        lang = resolve_lang(
            request.query_params.get("lang"),
            request.cookies.get(LANG_COOKIE),
        )
        return HTMLResponse(content=legal_html(page, lang))

    endpoint.__name__ = f"{page}_page"
    endpoint.__doc__ = f"Serve the static {page} page (en/pt)."
    return endpoint
