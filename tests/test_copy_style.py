"""User-facing copy must not use em or en dashes.

The product voice uses periods, colons, pipes and middle dots instead. This
test keeps that preference from regressing in the SPA strings, the legal pages,
the document head and the crawler documents. Developer prose (README, docs and
code comments) is deliberately out of scope.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import pytest

from preconsult.core.i18n import translations
from preconsult.site.seo import LLMS_TXT

ROOT = Path(__file__).resolve().parents[1]
DASHES = {
    "\u2014": "em dash",
    "\u2013": "en dash",
}


def _strings(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            yield from _strings(item, child)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")


def _offenders(label: str, text: str) -> list[str]:
    return [f"{label}: {name}" for char, name in DASHES.items() if char in text]


def test_translations_use_no_long_dashes():
    offenders = [
        offender
        for lang, values in translations.items()
        for path, text in _strings(values)
        for offender in _offenders(f"i18n[{lang}].{path}", text)
    ]

    assert offenders == []


def test_document_and_legal_copy_use_no_long_dashes():
    files = [
        ROOT / "web" / "index.html",
        *sorted((ROOT / "web" / "legal").glob("*.html")),
    ]
    offenders = [
        offender
        for path in files
        for offender in _offenders(str(path.relative_to(ROOT)), path.read_text())
    ]

    assert offenders == []


def test_crawler_copy_uses_no_long_dashes():
    assert _offenders("llms.txt", LLMS_TXT) == []


@pytest.mark.parametrize("lang", ["en", "pt"])
def test_generated_contracts_use_no_long_dashes(lang):
    path = ROOT / "contracts" / "i18n" / f"{lang}.json"
    payload = json.loads(path.read_text())
    offenders = [
        offender
        for key, text in _strings(payload)
        for offender in _offenders(f"{path.relative_to(ROOT)}.{key}", text)
    ]

    assert offenders == []
