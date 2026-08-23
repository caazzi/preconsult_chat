# AGENTS.md — Engineering Guidelines for PreConsult

Rules for any agent (or human) working in this repository.

## Deployment: CI/CD is the ONLY path

**Never push; commit and stop.** Agents do NOT run `git push`, `git merge`/merge PRs, or any
remote-write operation. Commit changes locally and stop — the human decides when and how to get
them to `main`. Deploying is the human's job and happens only via the pipeline below (or their own
push). Note that pushing may also fail for auth reasons unless the token has the `workflow` scope.

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
- Run the test suite **with the coverage gate** (this is the exact CI command):
  ```bash
  uv run python -m pytest tests/ -v --cov --cov-report=term-missing --cov-fail-under=80
  ```
  Do not run `pytest` without `--cov` — the suite is considered "not done" if overall branch
  coverage drops below 80% (measured over `src/preconsult` + `reflex_app/preconsult`, omitting the
  generated Reflex page tree in `reflex_app/preconsult/preconsult.py`).
- For deploy-affecting changes, the task is NOT done until the CI/CD-built revision serves `200`.

## Testing the Reflex frontend (state.py) — hard-won constraints

These are reflex-specific rules that WILL bite if ignored:

- `State()` can only be instantiated when running under pytest's test environment
  (`is_testing_env()` is true); it raises `ReflexRuntimeError` otherwise. Keep state tests inside
  `tests/` and never `python -c`-instantiate reflex state ad hoc.
- **Never `await` a chained background `@rx.event(background=True)` handler directly.** Reflex wraps
  background handlers so calling `await self.some_background_handler()` raises
  `RuntimeError: Cannot directly call background task ... use yield/return`. `init_session` chains
  into `get_interview_questions` this way, which is WHY the payload construction was factored out
  into the pure `build_session_init_payload()` function. To test a background handler, call its raw
  body via `State.<handler>.fn(state)` (the `.fn` attribute holds the unwrapped coroutine), and to
  test a handler that chains into another background handler, patch the nested handler to a no-op.
- Setting `state.router` for `detect_lang` / `AdminState` tests fails because `router` is a reflex
  inherited var; use `object.__setattr__(state, "router", fake)` instead.
- `state._api_url()` prefixes `/api`; if `API_BASE_URL` already ends in `/api` the request path
  becomes `/api/api/...`. In tests, mock the HTTP layer by matching on `request.url.path.endswith(...)`
  (or ignoring the path) rather than exact-match on `/api/...`.
- Question/emergency parsing lives in `src/preconsult/core/parsing.py` (`split_questions`,
  `is_emergency_trigger`) and is shared by the backend and `state.py`. Update the parser there and
  `tests/test_question_parsing.py` — do NOT re-inline the regex in `state.py`.

## Observability & the zero-PHI rule

- PreConsult must never log or expose health data. `preconsult/core/observability.py` intentionally
  only accepts metadata (event name, request id, language, counts, timings) and truncates
  free-text-derived lengths — NEVER log chief complaint, conditions, medications, answers, or
  complaint detail values. Only non-content counters (e.g. `len(...)`) are allowed.
- Every error response carries a stable machine-readable `code` (`auth_failed`, `rate_limited`,
  `session_expired`, `validation_failed`, `redis_unavailable`, `llm_unavailable`,
  `ai_upstream_error`, `service_unavailable`, `internal_error`). Do not rename/remove codes casually —
  `tests/test_error_handlers.py` and `tests/test_api_integration.py` assert them, and CI/alerts key
  on them. Responses must stay generic (never leak exception internals or user values).

## Client-IP & proxy trust

- `get_client_ip()` only honors `cf-connecting-ip` / `x-forwarded-for` when `TRUST_PROXY_HEADERS=true`
  (`src/preconsult/core/config.py`). Leave it `false` unless the app genuinely sits behind a trusted
  fronting proxy — otherwise spoofed headers bypass per-IP rate limits / quotas. Tests in
  `tests/test_client_ip.py` lock this policy.

## Secrets & environment

- `.env` is secret and must not be read or edited for value changes without care; secrets live in
  Google Secret Manager (`SECUREMED_API_KEY`, `REDIS_URL`) and are wired as secret references, not
  plaintext env vars, in every deploy.
- Deploy-affecting changes include anything the container runs: error-response shape (codes),
  health routes, config flags (e.g. `TRUST_PROXY_HEADERS`), Sentry init. Such a change is only
  "done" after the CI/CD-built revision serves `200` — local commits alone are NOT deployment.
