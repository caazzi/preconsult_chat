# AGENTS.md — Engineering Guidelines for PreConsult

Rules for any agent (or human) working in this repository.

## Deployment: CI/CD is the ONLY path

**Do not deploy to production with ad-hoc commands.** The serving container is deployed EXCLUSIVELY
through the GitHub Actions pipeline at `.github/workflows/ci-cd.yml`.

- **NEVER run `gcloud run deploy --source .`** or any manual image rebuild.
  Cloud Build `cloud-run-source-deploy` images have proven unservable (they boot but return
  `502` / `upstream connect error or disconnect/reset before headers. reset reason: protocol error`).
  Only CI-built images in the `securemed-repo` Artifact Registry are verified to serve.
- To ship a change to the running app:
  1. Commit + push to `main` (CI auto-deploys on merge), **or** trigger
     **GitHub Actions → PreConsult CI/CD → *Run workflow*** (workflow_dispatch).
  2. Confirm the deployed revision passes a smoke test (e.g. `GET /health` → 200) before marking done.
- If you must deploy an already-built CI image without rebuilding, use
  `scripts/deploy_backend.sh cost_optimized [image_ref]`. This script never runs `--source`.

## Verification before you claim a task is done

- Lint the code you changed with ruff: `uv run ruff check .`
- Run the test suite: `uv run python -m pytest tests/ -v`
- For deploy-affecting changes, the task is NOT done until the CI/CD-built revision serves `200`.

## Secrets & environment

- `.env` is secret and must not be read or edited for value changes without care; secrets live in
  Google Secret Manager (`SECUREMED_API_KEY`, `REDIS_URL`) and are wired as secret references, not
  plaintext env vars, in every deploy.
