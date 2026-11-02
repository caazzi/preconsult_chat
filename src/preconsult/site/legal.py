"""Static legal pages, served by the backend without Reflex.

The privacy/terms documents are plain HTML files under ``web/legal``. Keeping
them as files (not Python string literals) means they can be prerendered into
the SPA bundle later, and it keeps ~300 lines of inline markup out of the
frontend host module.

Nothing here depends on Reflex: the migration target is a plain FastAPI app
that serves the same documents at the same URLs.
"""

from __future__ import annotations

import html
import os
import re
from functools import lru_cache
from pathlib import Path

from preconsult.core.providers import active_disclosure

LEGAL_PAGES = ("privacy", "terms")
LEGAL_LANGUAGES = ("en", "pt")
DEFAULT_LANG = "en"

LANG_COOKIE = "preconsult_lang"

# The provider/model disclosure is the only part of the policy that changes
# with configuration. The documents carry these placeholders; everything else
# is prose and stays in the files.
_DISCLOSURE_FIELDS = {
    "LLM_PROCESSOR": "processor",
    "LLM_ENDPOINT": "endpoint",
    "LLM_TRAINING": "training",
}
_DISCLOSURE_PLACEHOLDER = re.compile(r"\{\{(LLM_[A-Z_]+)\}\}")


def _render_disclosure(document: str, lang: str) -> str:
    """Fill provider placeholders in ``document``, escaping their values.

    Plugging a value in without escaping would let a model id from configuration
    inject markup. ``quote=False`` keeps apostrophes in "Anthropic's" literal
    while still escaping ``<``, ``>`` and ``&`` for an HTML text node.

    A document that never references a placeholder still renders: this is a
    substitution, not a template engine. Unknown ``{{LLM_...}}`` tokens are left
    in place so a typo is visible (and caught by tests) instead of silently
    rendering nothing.
    """
    disclosure = active_disclosure(lang)

    def substitute(match: re.Match[str]) -> str:
        field = _DISCLOSURE_FIELDS.get(match.group(1))
        if field is None:
            return match.group(0)
        return html.escape(disclosure[field], quote=False)

    return _DISCLOSURE_PLACEHOLDER.sub(substitute, document)


def _candidate_dirs() -> list[Path]:
    """Places ``web/legal`` may live, most specific first.

    ``LEGAL_DIR`` wins so a deployment (or a test) can point at an explicit
    directory. The remaining candidates cover the three ways this module is
    imported: from the source tree, from an installed wheel in ``.venv``
    (while the process runs at the repo root), and inside the container where
    the code lives at ``/app/src`` and the process runs from ``/app``.
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
    """Return the HTML document for ``page`` in ``lang``.

    The cached file read is raw; the provider disclosure is substituted per
    request so it follows ``LLM_PROVIDER``/``LLM_MODEL``.
    """
    if page not in LEGAL_PAGES:
        raise ValueError(f"unknown legal page: {page}")
    if lang not in LEGAL_LANGUAGES:
        raise ValueError(f"unsupported legal language: {lang}")
    document = _read(str(legal_dir() / f"{page}.{lang}.html"))
    return _render_disclosure(document, lang)


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
