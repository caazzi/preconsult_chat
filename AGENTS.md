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
- `/health` probes are TTL-throttled; tests that mock `check_redis_health` /
  `probe_event_channel` must clear the cache with `_reset_health_probe_cache_unlocked()`
  (or rely on the conftest fixture) or a warm cache will mask the mock.
- The served `api` object is wrapped by `_BotGateMiddleware`. Tests POSTing to
  `/api/*` use httpx's default UA (passes the gate); don't set scanner-like UAs
  (e.g. `curl`) in API tests or the 403 gate will intercept before the endpoint.

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

## Redis is reserved for real users (free tier)

The app runs on a **free-tier serverless Redis (Upstash)** with a finite daily
request quota. Non-user traffic burned the quota (and caused `session_expired`
outages), so Redis must be reserved for actual patient sessions:

- **NEVER set `redis_url` in `reflex_app/rxconfig.py`.** Pointing Reflex at Redis
  spins up its `RedisTokenManager` (continuous keyspace/pubsub + per-socket token
  ops on every `/_event` connect), which exhausts the quota. Reflex state stays
  in-memory per instance (Cloud Run `--session-affinity`); the app's own
  `session_service` owns real sessions.
- **`/health` + `/health/ready` throttle their Redis/socket probes** (~1/min) via
  `_throttled_probe` in `preconsult.py`. Don't reintroduce a per-request Redis
  ping — CI/scanners/readiness polling would drain the quota.
- **The deployed CI smoke test is liveness/socket-only.** Full session/stream/
  rate-limit/SSE coverage runs in the `test` job against a local `redis:alpine`.
  Don't add session-create/stream stages to the deployed smoke test.
- **`State.log_analytics_event` is a no-op until a real session exists**
  (`session_id` set) — bots that never start the flow must not reach the
  analytics Redis write path. Keep that gate when touching analytics.
- **A conservative bot gate** (`_BotGateMiddleware` in `preconsult.py`) blocks
  scanner/CLI user-agents on Redis-backed `/api/*` paths with a fast `403` before
  storage. Browsers pass through; `/_event` no longer touches Redis, so it stays
  ungated.

## Session errors: redis_unavailable vs session_expired vs redis_quota_exceeded

- `get_session` **raises `RedisUnavailableError`** (→ stable 503 `redis_unavailable`)
  when Redis is down AND there is no in-memory fallback copy; it returns `{}` only
  for a genuine miss (→ 404 `session_expired`). Do NOT collapse an outage into a
  misleading `session_expired`.
- An Upstash **`max requests limit exceeded`** error (`_is_quota_error`) raises
  **`RedisQuotaExceededError`** → stable 503 `redis_quota_exceeded`, distinct from
  `redis_unavailable`, so "daily quota spent" is not confused with a general outage.
  Session CRUD/`check_redis_status` classify it; `/health` reports
  `redis: "quota_exceeded"` + code `redis_quota_exceeded`. Keep this distinct signal.
- Session CRUD has a best-effort per-worker in-memory fallback for transient Redis
  errors. It is a resilience shim, not a store of truth.

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
