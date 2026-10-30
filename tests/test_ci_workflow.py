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

The preflight step is pinned too. It is the thing that turns "the build
succeeded, then gcloud failed on a secret nobody created" into a five-second
named failure, and it is only useful if it covers every secret the deploy
actually references.
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "ci-cd.yml"
DRIFT_WORKFLOW = WORKFLOWS / "deploy-drift.yml"

ENV_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S.*$")
# Cloud Run secret refs are `env=SECRET_NAME:version`.
SECRET_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+$")
PREFLIGHT_LOOP = re.compile(r"for name in ([A-Z0-9_ ]+); do")


def _workflow(path: Path = WORKFLOW) -> dict:
    return yaml.safe_load(path.read_text())


def _deploy_steps() -> list[dict]:
    return _workflow()["jobs"]["deploy"]["steps"]


def _deploy_inputs() -> dict:
    step = next(
        s for s in _deploy_steps() if "deploy-cloudrun" in str(s.get("uses", ""))
    )
    return step["with"]


DEPLOY_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "deploy_backend.sh"
STARTUP_PROBE = (
    "--startup-probe=httpGet.path=/health/live,httpGet.port=8080,"
    "periodSeconds=10,timeoutSeconds=2,failureThreshold=10"
)


def _profile_flags_script() -> str:
    step = next(
        s
        for s in _deploy_steps()
        if s.get("name") == "Set Deployment Flags for Profile"
    )
    return step["run"]


def test_both_profiles_probe_readiness_over_http_not_tcp():
    """gunicorn binds :8080 before the worker finishes importing the app.

    A TCP probe therefore marks the instance ready while the app is still
    importing, and the first request is routed into the half-booted worker.
    /health/live is dependency-free and only answers once the ASGI app is up.
    """
    script = _profile_flags_script()

    assert STARTUP_PROBE in script
    assert script.count("$STARTUP_PROBE") == 2, (
        "both deploy profiles must append the HTTP startup probe"
    )
    assert "tcpSocket" not in script


def test_manual_deploy_script_uses_the_same_startup_probe():
    """The manual image-only path must not reintroduce the TCP probe."""
    assert STARTUP_PROBE in DEPLOY_SCRIPT.read_text()


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


def _preflight_secret_names() -> set[str]:
    step = next(
        s for s in _deploy_steps() if s.get("name") == "Verify required secrets exist"
    )
    match = PREFLIGHT_LOOP.search(step["run"])
    assert match, "the preflight no longer loops over a `for name in ...` list"
    return set(match.group(1).split())


def test_preflight_covers_exactly_the_secrets_the_deploy_references():
    referenced = {
        line.split("=", 1)[1].split(":", 1)[0]
        for line in _deploy_inputs()["secrets"].splitlines()
        if line.strip()
    }

    assert _preflight_secret_names() == referenced, (
        "the preflight check and the deploy `secrets:` block have drifted apart; "
        "a secret missing from the preflight fails late, after the container build"
    )


def test_preflight_runs_before_the_container_build():
    names = [str(step.get("name", "")) for step in _deploy_steps()]

    assert names.index("Verify required secrets exist") < names.index(
        "Build and Push Container"
    )


def test_drift_check_watches_the_service_this_pipeline_deploys():
    """The canary is only useful if it looks at the same Cloud Run service."""
    pipeline_env = _workflow()["env"]
    drift_env = _workflow(DRIFT_WORKFLOW)["env"]

    for key in ("PROJECT_ID", "REGION", "SERVICE_NAME"):
        assert drift_env[key] == pipeline_env[key], (
            f"{key} differs between ci-cd.yml and deploy-drift.yml"
        )


def test_drift_check_is_scheduled_and_compares_against_main():
    workflow = _workflow(DRIFT_WORKFLOW)
    # PyYAML resolves the `on:` key as boolean True (YAML 1.1).
    triggers = workflow.get("on", workflow.get(True))

    assert triggers["schedule"], (
        "the drift check must run on a schedule, not only on demand"
    )
    scripts = "\n".join(
        str(step.get("run", "")) for step in workflow["jobs"]["drift"]["steps"]
    )
    assert "commit-sha" in scripts, "the check must read the deployed commit label"
    assert "rev-parse HEAD" in scripts, (
        "the check must compare against the checked-out main commit"
    )


def _drift_step(name: str) -> dict:
    workflow = _workflow(DRIFT_WORKFLOW)
    return next(s for s in workflow["jobs"]["drift"]["steps"] if s.get("name") == name)


def test_drift_check_reads_the_serving_revision_not_the_service_label():
    """A failed deploy still updates the service template and its labels.

    On 2026-10-26 the service label said ``11c4c9c`` while 100% of traffic was
    on a revision built from ``bba3157``. Comparing the *service* label would
    therefore have reported "production is serving main" while production served
    a seven-week-old build - the false negative this job exists to prevent.
    """
    read_script = _drift_step("Read the serving revision")["run"]
    fail_script = _drift_step("Fail when production is not running main")["run"]

    assert "run revisions describe" in read_script, (
        "the commit must come from the serving revision"
    )
    assert "template_commit" in read_script
    assert "revision_ready" in fail_script, (
        "an unready serving revision must fail the check"
    )


def test_drift_parsers_tolerate_control_characters_in_gcloud_json():
    """gcloud emits raw newlines inside a condition message.

    ``--format=json`` serialises a multi-line ``Ready`` message (e.g. the three
    missing-secret errors) as a literal newline inside the string, which strict
    JSON rejects. Parsing those payloads with ``json.load`` failed in practice.
    """
    read_script = _drift_step("Read the serving revision")["run"]

    assert "json.load(" not in read_script
    assert read_script.count("strict=False") >= 4


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
