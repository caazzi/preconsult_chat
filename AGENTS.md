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
- **The `cost_optimized` profile (the default) keeps `--min-instances 1`, `--session-affinity` and a
  single worker on purpose, but none of them is a correctness requirement any more.** They were
  introduced for Reflex's in-memory Engine.IO session store, which no longer exists: the wizard runs
  in the browser and the session of record is in Redis, so an instance recycle does not lose a
  user's next event. What is still per-worker is only the **best-effort** Redis-outage fallback
  (the `_memory_sessions` shim in `services/session_service.py`) and the rate-limit fallback
  (`MemoryRateLimitStore`) — resilience shims, not stores of truth, so a user landing on a worker
  without its fallback copy degrades to an error rather than to silent data loss. **What would prove
  multi-worker / scale-to-zero safe** is a measured load test showing those shims are never the path
  a real user depends on (as long as Redis is healthy, sessions live in Redis and any worker can
  serve them). Until that measurement lands, do NOT loosen the flags, and do not describe the
  current choice as required for correctness. The profile stays a 24/7 **0.5 vCPU / 1Gi** warm
  instance (a warm instance also removes cold-start latency for a portfolio app with idle gaps).
  `--concurrency 1` MUST stay paired with `cpu=0.5`: Cloud Run rejects `cpu < 1` when
  `concurrency > 1` ("Total cpu < 1 is not supported with concurrency > 1"). (`high_performance`
  intentionally keeps `min=2` and `concurrency=40` for latency, but is opt-in only.)
- If you must deploy an already-built CI image without rebuilding, use
  `scripts/deploy_backend.sh cost_optimized [image_ref]`. This script never runs `--source`.

## Verification before you claim a task is done

- Lint the code you changed with ruff: `uv run ruff check .`
- Sync dev environments with `uv sync --locked --all-extras --dev`. The Bedrock client tests
  need the `bedrock` extra even though the image installs Vertex only.
- Run the test suite **with the coverage gate** (this is the exact CI command):
  ```bash
  uv run python -m pytest tests/ -v --cov --cov-report=term-missing --cov-fail-under=80
  ```
  Do not run `pytest` without `--cov` — the suite is considered "not done" if overall branch
  coverage drops below 80%. Coverage is measured over **`src/preconsult` only** (`pyproject.toml`
  `[tool.coverage.run]`); `web/` is covered by its own Vitest suite, not by the Python gate.
- Frontend changes: `cd web && npm run lint && npm run test && npm run build`. CI installs with
  `uv sync --locked` and `npm ci`, so **a stale `uv.lock` must fail the build, not silently
  re-resolve** — re-lock locally and commit the lockfile with the dependency change.
- Browser E2E (only when you touch the SPA or the host): `scripts/run_e2e_spa.sh`.
- For deploy-affecting changes, the task is NOT done until the CI/CD-built revision serves `200`.

## Serving topology: one app, one process

- `src/preconsult/host.py` (`preconsult.host:app`) is the **only** served app — there is no second
  frontend host and no state socket. It is a Starlette app wrapping
  **`BotGateMiddleware -> RequestIDMiddleware -> Starlette/GZip`**, mounting `/api` (FastAPI
  sub-app) first, then health, crawler documents (`/robots.txt`, `/sitemap.xml`, `/llms.txt`), legal
  pages (`/privacy`, `/terms`) and the React SPA at `/` **last**.
- That registration order is the contract (Starlette matches first-registered-wins; the SPA mount is
  a catch-all). `tests/test_host_app.py` pins the composition (registration order, middleware order,
  and the root-mount rule that a scanner probe or a deleted backend prefix must never receive the
  SPA shell).
- `site/static.py::SPAStaticFiles` owns the document contract: the shell is `no-store`, real files
  under `/assets` are content-hashed + immutable, an unknown *navigation* falls back to the shell,
  and a missing *file* stays a 404. Keep the explicit scanner-probe / backend-prefix 404s — a path
  the router does not know must not be answered with HTML.
- The app resolves the bundle from `WEB_DIST_DIR`, then `./web/dist`, then `../web/dist`; a missing
  bundle is logged as a packaging error (path only, PHI-free) instead of becoming a silent root 404.
- **The frontend holds no API key.** The SPA authenticates with the HttpOnly session cookie minted
  by `POST /api/session/init`, which is why `ALLOW_PUBLIC_INIT=true` in the deployed environment is
  load-bearing. Keep the bootstrap guarded by the per-IP limits, the bot gate and the
  `SessionInitRequest` bounds (see `docs/authz-matrix.md`).
- The served `api` object sits behind `BotGateMiddleware` (`src/preconsult/site/middleware.py`).
  Tests POSTing to `/api/*` use httpx's default UA (passes the gate); don't set scanner-like UAs
  (e.g. `curl`) in API tests or the 403 gate will intercept before the endpoint.

## Testing the React frontend (`web/`)

- The SPA is React 18 + Vite + TypeScript, tested with **Vitest** (`cd web && npm run test`) and
  built with `npm run build` (`tsc -b && vite build`) into `web/dist`, which the host mounts at `/`.
- **Do not hand-copy i18n strings or parsing behaviour into the SPA.** `src/preconsult/core/i18n.py`
  and `core/parsing.py` are the sources of truth; `scripts/export_contracts.py` generates
  `contracts/*.json` and `cd web && npm run sync:contracts` copies them into
  `web/src/contracts/generated/`. CI regenerates and fails on any drift, so a Python-side copy change
  must ship with the regenerated artifacts. Never edit `web/src/contracts/generated/*` by hand.
- The wizard is entirely client-side (landing → 4 form steps → Q&A → summary/PDF, plus the
  emergency dialog). Language comes from `?lang=` then `navigator.language`, and is mirrored back
  into the URL — **no cookie and no `localStorage`/`sessionStorage` is written**
  (`site/legal.py` still reads a legacy `preconsult_lang` cookie if an old browser sends one).
- Because nothing is persisted, the wizard registers a `beforeunload` confirm as soon as the intake
  starts: an accidental reload, back-swipe or closed tab would otherwise silently erase every answer.
  It is deliberately **skipped on the emergency screen** — that exit must never be interrupted. Keep
  both behaviours. Likewise every Q&A question must stay answerable with an explicit localised
  "I don't know" (`answer_unknown`): an empty answer is rejected, a *stated* unknown is not — forcing
  a patient to type something invents clinical data.
- The browser E2E job (`tests/e2e_spa`, driven by `scripts/run_e2e_spa.sh`) boots the real
  `preconsult.host:app`, serves the built SPA at `/`, and mocks `/api` at the browser route layer —
  no live LLM provider or serverless Redis. It asserts the SPA boots, walks the wizard, and writes
  no client storage.

## Observability & the zero-PHI rule

- PreConsult must never log or expose health data. `preconsult/core/observability.py` intentionally
  only accepts metadata (event name, request id, language, counts, timings) and truncates
  free-text-derived lengths — NEVER log chief complaint, conditions, medications, answers, or
  complaint detail values. Only non-content counters (e.g. `len(...)`) are allowed.
- Every structured event is tagged with `revision` (`GIT_SHA`/`K_REVISION`) so logs are attributable
  to a deployed build. Keep that tag; do not drop it.
- Emergency detection must NOT rest solely on the LLM's output. `has_emergency_red_flag`
  (`core/parsing.py`, reusing the `is_emergency_trigger` token list) gates the stream endpoints on
  the patient-supplied chief complaint / detail BEFORE any model call; a hit short-circuits to a
  localized emergency SSE event (`stream.initial.emergency_input` / `stream.interview.emergency_input`,
  metadata-only, `trigger_side=input`) and the LLM is never invoked. Keep the input gate in front of
  the output-side `is_emergency_trigger` client check (`web/src/contracts/parsing.ts`).
- The intake draft is NOT persisted to `localStorage` (or any client store): it would outlive tab
  close and contradict the zero-retention promise. Do not reintroduce client-side PHI persistence;
  `tests/test_security.py::TestP9_NoPHIDraftPersistence` and the Playwright no-storage check guard
  this.
- `site/request_id.py::RequestIDMiddleware` stamps `x-request-id`, emits a PHI-safe `http.request`
  log line (method + path only, no query string) and counts outcomes as `http.status.<code>`. A 404
  under `/assets` is counted and logged as **`static.asset_404`** — the tell that a cached document
  references chunks the current build does not have. Both are exposed read-only via
  `GET /health/metrics` (in-memory, per-worker, PHI-free, never Redis). Keep these PHI-safe: only
  path/status/event-name keys, never user content.
- Every error response carries a stable machine-readable `code` (`auth_failed`, `bot_blocked`,
  `rate_limited`, `session_expired`, `validation_failed`, `redis_unavailable`,
  `redis_quota_exceeded`, `llm_unavailable`, `ai_upstream_error`, `service_unavailable`,
  `internal_error`). Do not rename/remove codes casually — `tests/test_error_handlers.py`,
  `tests/test_api_integration.py` and `web/src/api/client.ts` assert them, and CI/alerts key on
  them. Responses must stay generic (never leak exception internals or user values).
- `/health` probes are TTL-throttled; tests that mock `check_redis_health` /
  `check_redis_status` must clear the cache with `_reset_health_probe_cache_unlocked()`
  (or rely on the conftest fixture) or a warm cache will mask the mock. The handlers and the cache
  live in `src/preconsult/site/health.py`, and the interactive probe is a **per-app parameter**
  (`register_health_routes(app, event_channel_probe=...)`), not a module global — pass it when
  building the app (`build_asgi_app(event_channel_probe=...)`). Nothing sets it today, so `/health`
  reports `event_channel: "not_configured"`; that is expected, not a broken probe.

## Redis is reserved for real users (free tier)

The app runs on a **free-tier serverless Redis (Upstash)** with a finite daily
request quota. Non-user traffic burned the quota (and caused `session_expired`
outages), so Redis must be reserved for actual patient sessions:

- **Nothing may open a Redis connection at import/startup or per health poll.** The app's own
  `session_service` owns real sessions; there is no framework session/token manager left to feed.
  A new background task, pub/sub subscription or per-connection ping is a quota regression even when
  it looks like infrastructure.
- **`/health` + `/health/ready` throttle their Redis probes** (~1/min) via `_throttled_probe` in
  `src/preconsult/site/health.py`. Don't reintroduce a per-request Redis ping — CI/scanners/readiness
  polling would drain the quota.
- **The deployed CI smoke test is document/health-only (stages 1–5: health, `/` document + head
  contract, asset graph, served revision, legal pages).** Full session/stream/rate-limit/SSE
  coverage runs in the `test` job against a local `redis:alpine`. Don't add session-create/stream
  stages to the deployed smoke test.
- **Analytics have two tiers, and only one touches Redis.** The four pre-session steps
  (`intake_started` … `history_submitted`) are counted in memory (`funnel.*` in
  `GET /health/metrics`) and logged, because no session exists until the lifestyle step — they must
  never write to Redis. The three session steps stay gated on a real `session_id`
  (`logEvent` in `web/src/api/analytics.ts`), so bots that never start the flow cannot reach the
  analytics write path. Keep both: the server-side split (`ANONYMOUS_FUNNEL_EVENTS` + the
  `FunnelEvent` whitelist in `endpoints.py`) and the client gate.
- **A conservative bot gate** (`BotGateMiddleware` in `src/preconsult/site/middleware.py`) blocks
  scanner/CLI user-agents on the Redis-backed `/api/*` paths with a fast `403` before storage.
  Browsers pass through; the gate deliberately covers `/api/*` only (the SPA document and static
  assets are ungated and never touch Redis).

## Session errors: redis_unavailable vs session_expired vs redis_quota_exceeded

- `get_session` **raises `RedisUnavailableError`** (→ stable 503 `redis_unavailable`)
  when Redis is down AND there is no in-memory fallback copy; it returns `{}` only
  for a genuine miss (→ 404 `session_expired`). Do NOT collapse an outage into a
  misleading `session_expired`.
- An Upstash **`max requests limit exceeded`** error (`_is_quota_error`) is classified
  as `redis_quota_exceeded`, distinct from `redis_unavailable`, so "daily quota spent"
  is not confused with a general outage. Session CRUD/`check_redis_status` classify it;
  `/health` reports `redis: "quota_exceeded"` + code `redis_quota_exceeded`.
- **Quota exhaustion degrades to the per-worker in-memory store, it does NOT block the
  user.** `create_session`/`update_session` store in memory and succeed; `get_session`
  serves an in-memory copy when present and raises `RedisQuotaExceededError` only when it
  genuinely has nothing for that session id (surface the cause instead of an unknown `{}`).
  **The in-memory shim honours the same 30-minute TTL as Redis** (each copy expires and is
  pruned lazily on access) and is **capped at `_MEMORY_SESSIONS_MAX`** (oldest-by-expiry
  evicted) so a prolonged outage cannot accumulate unbounded PHI in a worker's RAM. Keep
  those guards when touching the fallback — they protect the zero-persistence privacy claim.
- Session CRUD has a best-effort per-worker in-memory fallback for transient Redis
  errors. It is a resilience shim, not a store of truth.
- The rate-limit / session-quota fallback (`MemoryRateLimitStore`) is capped at
  `_MEMORY_LIMITER_MAX_KEYS`, evicting expired counters first, then those closest to expiry. Its keys
  are per client IP and now genuinely vary per visitor, so the cap is what stops a long outage from
  growing a worker's dict for the life of the process (expired counters used to be dropped only when
  the same key returned). Tests: `tests/test_memory_limiter.py`.

## Client-IP & proxy trust

- **Measured on Cloud Run (2026-10-26, header-echo probe, service deleted after):** the container's
  transport peer is `169.254.169.126` — the local proxy, identical for every visitor. Cloud Run
  **appends** the real client to `X-Forwarded-For` and does **not** strip what the caller sent
  (`X-Forwarded-For: 1.2.3.4` arrives as `1.2.3.4,187.15.85.23`). `cf-connecting-ip` passes through
  untouched. Consequence: `TRUST_PROXY_HEADERS` must be `true` in the deployed container, and
  `get_client_ip()` (`src/preconsult/api/endpoints.py`) takes the **last** X-Forwarded-For hop,
  validated with `ipaddress`, falling back to the transport address. Trusting the leftmost hop or
  `cf-connecting-ip` would let a client rotate IPs and bypass the per-IP rate limits / 20-a-day
  session quota; trusting the transport peer alone makes those limits **global** (one shared bucket
  for all users). Caveat: `TRUST_CF_CONNECTING_IP` stays `false` unless `pre-consult.org` is moved
  behind Cloudflare's proxy. Tests in `tests/test_client_ip.py` lock this policy.
- Setting `TRUST_PROXY_HEADERS` without the right hop was a live bug, not a hardening nicety: with it
  off, every production user shared `169.254.169.126` in the quota key.

## Serving & the CDN/edge cache reality

- `pre-consult.org` is **DNS-only**: A/AAAA records point at Google Frontend IPs (`216.239.*`,
  `2001:4860:*`), **not** Cloudflare proxy IPs. Cloudflare hosts DNS but does **not** sit in the request
  path, so **purging the "Cloudflare cache" has no effect** on what users receive. Cache invalidation
  for the served document must target Google Frontend/Cloud CDN + a browser hard-refresh.
- The served **`index.html` shell is `no-store`** and its JS/CSS chunks are content-hashed +
  immutable (`site/static.py`). A stale `index.html` references chunk URLs that 404 on the current
  revision; the app JS never loads and the user gets a blank page, with `static.asset_404`
  counters/logs on the server as the signature. If that recurs, first **hard-purge the document**
  (it is a stale-shell symptom) — do not "fix" it by touching asset caching or the bundle layout.
- The CI smoke test asserts the `no-store` document contract, the document head (title, `og:image`,
  and no `noindex`) and that the full `index.html` asset graph resolves 200 (stages 2 & 3). A deploy
  that regresses document caching or ships an incomplete bundle fails loudly.

## Legal, SEO & i18n

- `web/legal/*.html` (`privacy.{en,pt}.html`, `terms.{en,pt}.html`) is now the **only** copy of the
  policy text. It is read at request time by `src/preconsult/site/legal.py`, which serves `/privacy`
  and `/terms` at the same URLs the SPA links to. The CI smoke test asserts every page in both
  languages against the deployed revision — a missing file is a compliance failure, not cosmetics.
- Legal pages pick their language from `?lang=`, then a legacy `preconsult_lang` cookie, then
  English (`resolve_lang`). The SPA keeps its language in the URL only, so the cookie is read for
  old browsers; do not add a new cookie for language.
- UI copy and the shared parsers have one source of truth: `src/preconsult/core/i18n.py` and
  `core/parsing.py`, exported to `contracts/*.json` and copied into `web/src/contracts/generated/`.
  Change the Python side, regenerate, and commit both.
- Crawler documents live in `src/preconsult/site/seo.py` and are wired by `site/routes.py`
  (`/robots.txt`, `/sitemap.xml` with `pre-consult.org` URLs, `/llms.txt`). Keep them out of the
  OpenAPI schema.

## Secrets & environment

- `.env` is secret and must not be read or edited for value changes without care; secrets live in
  Google Secret Manager (`SECUREMED_API_KEY`, `REDIS_URL`, `SESSION_SECRET`) and are wired as secret
  references, not plaintext env vars, in every deploy. `SESSION_SECRET` signs the session cookie and
  is required at startup outside `BUILD_MODE`.
- **The active LLM provider is selected by `LLM_PROVIDER`, and the default is `vertex`
  (Google Vertex AI / Gemini), not Bedrock.** `core/llm.py` builds a `ChatVertexAI` client from
  `LLM_MODEL` + `VERTEX_REGION` + `PROJECT_ID`, or a `ChatBedrockConverse` client from
  `LLM_MODEL` + `BEDROCK_REGION` when `LLM_PROVIDER=bedrock`. **Bedrock lives in the
  `bedrock` optional extra**, so the default image does not install boto3/botocore (~34 MB) for a
  provider it has no credentials for: a Bedrock deployment must build with
  `uv sync --locked --extra bedrock` (the Dockerfile's plain `uv sync --locked` installs Vertex
  only), otherwise `get_llm()` raises a RuntimeError naming the extra. **Because uv resolves a
  single universal lock across extras, `langchain-aws` and `langchain-google-vertexai` must stay on
  the same `langchain-core` major — upgrade them in the same change**, or `uv lock` fails with an
  unsatisfiable `preconsult[bedrock]` (the constraint block in `pyproject.toml` records this). The default is the provider the deployed
  service actually has credentials for: production ran a Vertex build until 2026-09-08 and Bedrock
  credentials do not exist in Secret Manager, so a Bedrock-only `main` could not be deployed without
  breaking every question request. Bedrock is the planned next step, kept working behind the switch —
  do not delete either path.
  **Switching providers is a PHI decision, not a config tweak.** It changes which third party receives
  clinical text, so the privacy copy in `web/legal/privacy.en.html` and `web/legal/privacy.pt.html`
  (the only copies left) and the matching `src/preconsult/core/i18n.py` strings must change in the
  same commit, along with the deploy's `secrets:` block (add
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`), the `LLM_MODEL` default, and the IAM policy scope
  (`bedrock:InvokeModelWithResponseStream` on the single Haiku model).
  Upstream failures map to the existing stable codes via `google_api_handler` /
  `bedrock_api_handler` (throttling → `503 llm_unavailable`, everything else → `502
  ai_upstream_error`); keep those codes unchanged. Regions are fixed and must not be routed by UI
  language (language ≠ data residency).
- Deploy-affecting changes include anything the container runs: error-response shape (codes),
  health routes, config flags (e.g. `TRUST_PROXY_HEADERS`, `ALLOW_PUBLIC_INIT`), the served document
  and its cache headers, Sentry init. Such a change is only "done" after the CI/CD-built revision
  serves `200` — local commits alone are NOT deployment.
