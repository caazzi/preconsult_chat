"""
Tests for scripts/export_i18n_json.py.

Pins that the i18n JSON artifact produced for the future frontend is:
  - lossless (JSON round-trips to the same Python structure),
  - key-parity-safe (en and pt share identical key sets),
  - deterministic (stable, sorted-key output across runs),
  - value-type-preserving (nested lists such as gender/conditions options).
"""

import importlib.util
import json
import os
import shutil
import tempfile

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT_PATH = os.path.join(_PROJECT_ROOT, "scripts", "export_i18n_json.py")


def _load_exporter():
    """Import scripts/export_i18n_json.py by absolute path (not a package)."""
    spec = importlib.util.spec_from_file_location("export_i18n_json", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_export(mod) -> str:
    """Export to a fresh temp dir and return that directory path."""
    tmp = tempfile.mkdtemp(prefix="i18n_export_")
    mod.export(tmp)
    return tmp


def test_export_writes_en_and_pt():
    mod = _load_exporter()
    tmp = _run_export(mod)
    assert os.path.isfile(os.path.join(tmp, "en.json"))
    assert os.path.isfile(os.path.join(tmp, "pt.json"))
    shutil.rmtree(tmp, ignore_errors=True)


def test_export_is_lossless_round_trip():
    mod = _load_exporter()
    tmp = _run_export(mod)
    for lang, values in mod.load_translations().items():
        with open(os.path.join(tmp, f"{lang}.json"), encoding="utf-8") as fh:
            decoded = json.load(fh)
        assert decoded == values, f"{lang}.json did not round-trip losslessly"
    shutil.rmtree(tmp, ignore_errors=True)


def test_export_is_deterministic():
    mod = _load_exporter()
    a = _run_export(mod)
    b = _run_export(mod)
    for lang in mod.load_translations().keys():
        with open(os.path.join(a, f"{lang}.json"), encoding="utf-8") as fh:
            content_a = fh.read()
        with open(os.path.join(b, f"{lang}.json"), encoding="utf-8") as fh:
            content_b = fh.read()
        assert content_a == content_b, f"{lang}.json is not deterministic"
    shutil.rmtree(a, ignore_errors=True)
    shutil.rmtree(b, ignore_errors=True)


def test_export_en_and_pt_have_identical_keys():
    from reflex_app.preconsult.i18n import translations

    assert set(translations["en"].keys()) == set(translations["pt"].keys())


def test_export_preserves_nested_list_values():
    mod = _load_exporter()
    tmp = _run_export(mod)
    with open(os.path.join(tmp, "en.json"), encoding="utf-8") as fh:
        en = json.load(fh)
    assert isinstance(en["gender_opts"], list)
    assert isinstance(en["conditions_opts"], list)
    assert en["gender_opts"] == [
        "Prefer not to say",
        "Female",
        "Male",
        "Intersex",
    ]
    shutil.rmtree(tmp, ignore_errors=True)


def test_export_accepts_arbitrary_target_dir():
    """The exporter must not depend on a web/ stack being scaffolded yet."""
    mod = _load_exporter()
    tmp = tempfile.mkdtemp(prefix="i18n_target_")
    written = mod.export(tmp)  # arbitrary empty dir is a valid target
    assert len(written) == 2
    shutil.rmtree(tmp, ignore_errors=True)
