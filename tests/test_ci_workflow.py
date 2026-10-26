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


def _env_pairs() -> dict:
    return dict(
        line.split("=", 1)
        for line in _deploy_inputs()["env_vars"].splitlines()
        if line.strip()
    )


def test_the_required_runtime_inputs_are_wired():
    env = _env_pairs()
    secret_names = {
        line.split("=", 1)[0]
        for line in _deploy_inputs()["secrets"].splitlines()
        if line.strip()
    }

    assert {"API_BASE_URL", "LLM_PROVIDER", "LLM_MODEL", "VERTEX_AI_REGION"} <= set(env)
    # SESSION_SECRET is fatal at startup outside BUILD_MODE (core/config.py), so
    # dropping it from the deploy would produce a revision that cannot boot.
    assert {"SESSION_SECRET", "REDIS_URL", "PRECONSULT_API_KEY"} <= secret_names


def test_the_deploy_environment_matches_the_selected_provider():
    """Mixing providers bricks the deploy in two different ways.

    Bedrock env/secret refs on a Vertex deployment fail the revision outright
    when the AWS secrets do not exist (that is what blocked every deploy until
    2026-10-26). Vertex vars on a Bedrock deployment point the model at a Gemini
    id, so every call fails at runtime instead.
    """
    env = _env_pairs()
    secret_names = {
        line.split("=", 1)[0]
        for line in _deploy_inputs()["secrets"].splitlines()
        if line.strip()
    }
    provider = env["LLM_PROVIDER"]

    if provider == "bedrock":
        assert {"BEDROCK_REGION"} <= set(env)
        assert {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"} <= secret_names
    else:
        assert "BEDROCK_REGION" not in env
        assert not {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"} & secret_names


def test_the_workflow_owns_the_service_environment():
    """`merge` would carry stale refs forward forever.

    The failed deploys of 2026-10-26 merged AWS secret refs into the service
    template; with `merge` those survive even after they leave this file, so
    every later deploy keeps failing on secrets that do not exist.
    """
    inputs = _deploy_inputs()

    assert inputs["env_vars_update_strategy"] == "overwrite"
    assert inputs["secrets_update_strategy"] == "overwrite"
