"""
Contract-artifact tests.

Two guarantees:
  1. The committed artifacts under ``contracts/`` are byte-for-byte what the
     Python sources produce (no silent drift). Mirrors the CI check.
  2. The Python parsing implementation satisfies every vector in
     ``contracts/parsing_vectors.json`` — the SAME vectors the future
     TypeScript port must satisfy, so both sides are pinned to one source.
"""

import importlib.util
import json
import os
import shutil
import tempfile

import pytest

from preconsult.core.parsing import (
    split_questions,
    is_emergency_trigger,
    _EMERGENCY_TRIGGERS,
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONTRACTS_DIR = os.path.join(_PROJECT_ROOT, "contracts")
_EXPORTER_PATH = os.path.join(_PROJECT_ROOT, "scripts", "export_contracts.py")


def _load_exporter():
    spec = importlib.util.spec_from_file_location("export_contracts", _EXPORTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_vectors() -> dict:
    with open(os.path.join(_CONTRACTS_DIR, "parsing_vectors.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_committed_contracts_match_generated_output():
    """Regenerating contracts must not change the committed files.

    If this fails, run ``python3 scripts/export_contracts.py`` and commit the
    result — the Python source of truth changed and the artifacts drifted.
    """
    mod = _load_exporter()
    tmp = tempfile.mkdtemp(prefix="contracts_check_")
    try:
        mod.export(tmp)
        for rel in (
            os.path.join("i18n", "en.json"),
            os.path.join("i18n", "pt.json"),
            "emergency_tokens.json",
            "parsing_vectors.json",
        ):
            committed = os.path.join(_CONTRACTS_DIR, rel)
            generated = os.path.join(tmp, rel)
            with open(committed, encoding="utf-8") as fh:
                a = fh.read()
            with open(generated, encoding="utf-8") as fh:
                b = fh.read()
            assert a == b, f"contracts/{rel} is stale; run scripts/export_contracts.py"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_emergency_tokens_contract_matches_source():
    with open(os.path.join(_CONTRACTS_DIR, "emergency_tokens.json"), encoding="utf-8") as fh:
        tokens = json.load(fh)
    assert tokens == list(_EMERGENCY_TRIGGERS)


def _split_cases():
    return _load_vectors()["split_questions"]


def _emergency_cases():
    return _load_vectors()["is_emergency_trigger"]


@pytest.mark.parametrize("case", _split_cases(), ids=lambda c: c["name"])
def test_split_questions_vectors(case):
    assert split_questions(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", _emergency_cases(), ids=lambda c: c["name"])
def test_is_emergency_trigger_vectors(case):
    assert is_emergency_trigger(case["input"]) is case["expected"]
