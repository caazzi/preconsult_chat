#!/usr/bin/env python3
"""
Export the language-neutral runtime contracts consumed by any frontend stack.

The Python sources remain the single source of truth; this script emits
deterministic, diff-friendly JSON artifacts so a non-Python frontend (the
React SPA) can conform to the *same* behavior instead of hand-copying it and
drifting. Three artifacts are produced under ``contracts/``:

  contracts/i18n/{en,pt}.json   translations (from src/preconsult/core/i18n.py)
  contracts/emergency_tokens.json  red-flag token list (core/parsing.py)
  contracts/parsing_vectors.json   split_questions/is_emergency_trigger vectors
  contracts/funnel_events.json     funnel event keys + their storage tier
                                   (core/analytics.py)

The parsing vectors are authored here (data), then two test suites run them
against BOTH the Python implementation and (later) the TypeScript port, so a
divergence fails CI on either side.

Usage:
    python3 scripts/export_contracts.py [OUTPUT_DIR]
    (default OUTPUT_DIR: contracts/)

CI runs this and asserts the working tree is unchanged, so the artifacts can
never silently drift from the Python source.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")


def load_translations() -> dict:
    """Import the translations from the canonical source module."""
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)

    from preconsult.core.i18n import translations

    return translations


def _load_parsing():
    """Import core/parsing.py by file path.

    Loaded directly rather than by module name so the exporter keeps working
    when run from an arbitrary working directory.
    """
    import importlib.util

    path = os.path.join(SRC_DIR, "preconsult", "core", "parsing.py")
    spec = importlib.util.spec_from_file_location("_contract_parsing", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._EMERGENCY_TRIGGERS


def load_funnel_events() -> dict:
    """The funnel keys and their tier, from the canonical source module."""
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)

    from preconsult.core.analytics import (
        ANONYMOUS_FUNNEL_EVENTS,
        SESSION_FUNNEL_EVENTS,
    )

    return {
        "anonymous": list(ANONYMOUS_FUNNEL_EVENTS),
        "session": list(SESSION_FUNNEL_EVENTS),
    }


def _assert_key_parity(translations: dict) -> None:
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


# Parsing behavior vectors. Both the Python implementation and the future TS
# port must satisfy every case. Grouped by function for readability; the
# ordered `cases` list is what the tests iterate.
def _parsing_vectors() -> dict:
    split_cases = [
        {"name": "numbered_dot", "input": "\n1. One?\n2. Two?", "expected": ["One?", "Two?"]},
        {"name": "numbered_paren", "input": "1) One?\n2) Two?", "expected": ["One?", "Two?"]},
        {"name": "dash", "input": "- One?\n- Two?", "expected": ["One?", "Two?"]},
        {"name": "plain_newline_fallback", "input": "One?\nTwo?\nThree?", "expected": ["One?", "Two?", "Three?"]},
        {"name": "single_line", "input": "Just one?", "expected": ["Just one?"]},
        {"name": "empty", "input": "", "expected": []},
        {"name": "whitespace_only", "input": "   ", "expected": []},
        {"name": "crlf", "input": "1. One?\r\n2. Two?\r\n3. Three?", "expected": ["One?", "Two?", "Three?"]},
        {"name": "trailing_newlines", "input": "\n1. One?\n2. Two?\n\n\n", "expected": ["One?", "Two?"]},
        {"name": "mixed_separators", "input": "\n1. One?\n- Two?\n3) Three?", "expected": ["One?", "Two?", "Three?"]},
        {"name": "leading_spaces_after_marker", "input": "\n1.   One?\n2.    Two?", "expected": ["One?", "Two?"]},
        {
            "name": "multiline_question_body",
            "input": "\n1. Is this one long\nquestion spanning two lines?\n2. Second?",
            "expected": ["Is this one long\nquestion spanning two lines?", "Second?"],
        },
    ]
    emergency_cases = [
        {"name": "en_emergency", "input": "EMERGENCY: call 911", "expected": True},
        {"name": "en_911", "input": "please dial 911 now", "expected": True},
        {"name": "pt_accented", "input": "[ALERTA DE EMERGÊNCIA] ligue 192", "expected": True},
        {"name": "pt_unaccented", "input": "urgencia nao mencionada", "expected": True},
        {"name": "pt_titlecase", "input": "Urgência", "expected": True},
        {"name": "pt_upper_unaccented", "input": "URGENCIA", "expected": True},
        {"name": "non_emergency_questions", "input": "1. Question one?\n2. Question two?", "expected": False},
        {"name": "empty", "input": "", "expected": False},
        {"name": "unrelated_doctor", "input": "please ring my doctor today", "expected": False},
        {"name": "session_id_number", "input": "session id 1234", "expected": False},
        {"name": "benign", "input": "the patient is fine", "expected": False},
    ]
    return {
        "split_questions": split_cases,
        "is_emergency_trigger": emergency_cases,
    }


def _write_json(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def export(output_dir: str) -> list[str]:
    translations = load_translations()
    _assert_key_parity(translations)
    tokens = _load_parsing()

    written = []
    for lang, values in translations.items():
        path = os.path.join(output_dir, "i18n", f"{lang}.json")
        _write_json(path, values)
        written.append(path)

    tokens_path = os.path.join(output_dir, "emergency_tokens.json")
    _write_json(tokens_path, list(tokens))
    written.append(tokens_path)

    vectors_path = os.path.join(output_dir, "parsing_vectors.json")
    _write_json(vectors_path, _parsing_vectors())
    written.append(vectors_path)

    funnel_path = os.path.join(output_dir, "funnel_events.json")
    _write_json(funnel_path, load_funnel_events())
    written.append(funnel_path)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=os.path.join(PROJECT_ROOT, "contracts"),
        help="Output directory (default: contracts/)",
    )
    args = parser.parse_args()

    for path in export(args.output_dir):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
