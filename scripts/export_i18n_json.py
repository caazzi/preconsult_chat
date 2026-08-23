#!/usr/bin/env python3
"""
Export the PreConsult translations (reflex_app/preconsult/i18n.py) as
deterministic JSON consumed by a (future, non-Reflex) frontend.

The Python dict in i18n.py remains the single source of truth; this emits a
lossless, key-parity-checked, stable-ordered JSON artifact so any frontend
stack can load translations without re-copying 245 lines by hand.

Usage:
    python3 scripts/export_i18n_json.py [OUTPUT_DIR]
    (default OUTPUT_DIR: artifacts/i18n)

The generator is intentionally NOT wired into CI yet: it is a derived artifact
invoked on demand when scaffolding the new frontend. Tests in
tests/test_i18n_export.py pin its correctness and determinism.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFLEX_APP_DIR = os.path.join(PROJECT_ROOT, "reflex_app", "preconsult")


def load_translations() -> dict:
    """Import the i18n module without the project on the default sys.path."""
    if REFLEX_APP_DIR not in sys.path:
        sys.path.insert(0, REFLEX_APP_DIR)
    from i18n import translations

    return translations


def _assert_key_parity(translations: dict) -> None:
    """Fail loudly if the language dicts diverge in key sets."""
    langs = list(translations.keys())
    if len(langs) != 2:
        raise ValueError(f"Expected exactly 2 languages, got {langs}")
    en_keys, pt_keys = set(translations[langs[0]]), set(translations[langs[1]])
    missing_in_pt = en_keys - pt_keys
    missing_in_en = pt_keys - en_keys
    if missing_in_pt or missing_in_en:
        raise ValueError(
            "Translation key parity broken: "
            f"missing in PT: {sorted(missing_in_pt)}; "
            f"missing in EN: {sorted(missing_in_en)}"
        )


def export(output_dir: str) -> list[str]:
    """Write {lang}.json for each translation; return the written paths."""
    translations = load_translations()
    _assert_key_parity(translations)

    os.makedirs(output_dir, exist_ok=True)
    written = []
    for lang, values in translations.items():
        # sort_keys=True guarantees deterministic, diff-friendly output.
        payload = json.dumps(values, ensure_ascii=False, indent=2, sort_keys=True)
        path = os.path.join(output_dir, f"{lang}.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=os.path.join(PROJECT_ROOT, "artifacts", "i18n"),
        help="Output directory (default: artifacts/i18n)",
    )
    args = parser.parse_args()

    written = export(args.output_dir)
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
