"""The Cloud Run deploy step must keep comments out of its value blocks.

``google-github-actions/deploy-cloudrun`` forwards ``env_vars`` and ``secrets``
line by line without stripping ``#`` comments. A comment line therefore becomes
either an empty-valued environment variable (``env_vars``) or an invalid secret
reference (``secrets``), and the latter aborts the deploy before a revision is
created:

    ERROR: (gcloud.run.deploy) No secret version specified for
    # Per-session cookie signing key...:latest to reference the latest version.

That is exactly how the deploy on ``main`` failed on 2026-10-26, leaving
production on an older revision while the smoke test was skipped. The deploy
job is the only path that ships code, so this contract is pinned here: every
line inside those two blocks must be a real ``KEY=...`` entry.
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci-cd.yml"

ENV_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S.*$")
# Cloud Run secret refs are `env=SECRET_NAME:version`.
SECRET_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+$")


def _deploy_inputs() -> dict:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow["jobs"]["deploy"]["steps"]
    step = next(s for s in steps if "deploy-cloudrun" in str(s.get("uses", "")))
    return step["with"]


@pytest.mark.parametrize(
    ("key", "pattern"), [("env_vars", ENV_LINE), ("secrets", SECRET_LINE)]
)
def test_every_deploy_input_line_is_an_entry(key, pattern):
    value = _deploy_inputs()[key]
    lines = [line for line in value.splitlines() if line.strip()]

    assert lines, f"{key} must not be empty"
    for line in lines:
        assert pattern.match(line), (
            f"{key} entry is not a KEY=VALUE mapping: {line!r}. Comments inside "
            "this block are forwarded to gcloud verbatim and break the deploy; "
            "move them above the block."
        )


def test_the_required_runtime_inputs_are_wired():
    inputs = _deploy_inputs()

    env_names = {
        line.split("=", 1)[0]
        for line in inputs["env_vars"].splitlines()
        if line.strip()
    }
    secret_names = {
        line.split("=", 1)[0] for line in inputs["secrets"].splitlines() if line.strip()
    }

    assert {"API_BASE_URL", "BEDROCK_REGION", "LLM_MODEL"} <= env_names
    # SESSION_SECRET is fatal at startup outside BUILD_MODE (core/config.py), so
    # dropping it from the deploy would produce a revision that cannot boot.
    assert {"SESSION_SECRET", "REDIS_URL", "PRECONSULT_API_KEY"} <= secret_names
