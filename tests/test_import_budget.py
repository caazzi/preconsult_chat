"""Executable budget for the cold-start import of the served entrypoint.

``preconsult.main`` is what gunicorn imports before it can serve a single
request, so every module it pulls in is paid on each cold start. Three heavy
dependency trees are deliberately deferred until something actually needs them:

* ``sentry_sdk`` (+ its FastAPI integration) -> ``core.sentry.init_sentry``
* ``reportlab`` -> ``services.pdf_service.generate_pdf_report_in_memory``
* ``langchain_core`` (and its tracer/LangSmith stack) ->
  ``services.agent_service.get_interview_chain``

A module-scope ``import`` creeping back in would silently undo that, and no
functional test would fail: the app still works, just slower to boot. This test
is the invariant, asserted in a SUBPROCESS so the rest of the suite's imports
cannot mask a regression (pytest has usually imported langchain/pydantic by the
time a test runs).

It asserts *membership in* ``sys.modules``, never timing, so it is deterministic
on any machine.
"""

import json
import os
import subprocess
import sys

# Distribution top-levels that must NOT be imported by ``preconsult.main``.
# ``langchain_aws``/``botocore`` are checked too: the vendor path is already lazy
# in ``core.llm`` and this keeps it that way.
DEFERRED = (
    "langchain_aws",
    "langchain_core",
    "botocore",
    "reportlab",
    "sentry_sdk",
)

# Run outside the repo so python-dotenv cannot discover a developer's .env (which
# might set SENTRY_DSN and pull sentry_sdk in legitimately). The config module
# refuses to boot without the API key/secret; SENTRY_DSN is deliberately absent,
# matching the deployed environment.
_BASE_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "PRECONSULT_API_KEY": "import-budget-key",
    "SESSION_SECRET": "import-budget-secret",
}

_ENTRYPOINT_PROBE = (
    "import json, sys\n"
    "import preconsult.main\n"
    f"print(json.dumps(sorted(m for m in {DEFERRED!r} if m in sys.modules)))\n"
)

_PDF_PROBE = (
    "import json, sys\n"
    "import preconsult.services.pdf_service as pdf\n"
    "before = 'reportlab' in sys.modules\n"
    "data, name = pdf.generate_pdf_report_in_memory({}, [], 'en')\n"
    "print(json.dumps({\n"
    "    'before': before,\n"
    "    'after': 'reportlab' in sys.modules,\n"
    "    'bytes': len(data),\n"
    "    'name': name,\n"
    "}))\n"
)


def _run(probe: str, tmp_path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=dict(_BASE_ENV, HOME=str(tmp_path)),
        cwd=tmp_path,
        # Importing (or rendering a PDF) must never hang: no network at import.
        timeout=180,
    )


def test_importing_main_defers_heavy_dependencies(tmp_path):
    proc = _run(_ENTRYPOINT_PROBE, tmp_path)

    assert proc.returncode == 0, proc.stderr
    loaded = json.loads(proc.stdout.strip().splitlines()[-1])
    assert loaded == [], (
        f"preconsult.main imported {loaded} at module scope; defer them behind "
        f"the call site that needs them (see tests/test_import_budget.py)"
    )


def test_reportlab_loads_only_when_a_report_is_rendered(tmp_path):
    """The deferral is a timing change, not a removal: the renderer still works."""
    proc = _run(_PDF_PROBE, tmp_path)

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result["before"] is False, "importing pdf_service must not import reportlab"
    assert result["after"] is True, "rendering must import reportlab"
    assert result["bytes"] > 0
    assert result["name"].endswith(".pdf")
