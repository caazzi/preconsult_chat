# PreConsult — Privacy-First Medical Intake Assistant

An AI-powered web app that helps patients organize their symptoms before a doctor's visit. The core design constraint: **zero data persistence** — no database, no user accounts, no logs containing health data.

---

## The Problem

Patients arrive at consultations anxious and forget key details. Doctors have limited time. The gap between what the patient knows and what the doctor hears costs both sides.

PreConsult bridges that gap with a guided AI interview that generates a structured clinical summary — then destroys all data when the session ends.

---

## How It Works

1. **Landing & Privacy Choice**: Patient reviews privacy guarantees, chooses language (EN/PT), and starts intake.
2. **Demographics & Chief Complaint**: Patient fills age, sex, specialist, chief complaint, and duration.
3. **Medical History & Lifestyle**: Patient selects pre-existing conditions (or "None"), medications, allergies, family history, and smoking/alcohol habits.
4. **Clinical Assessment**: The AI generates targeted follow-up questions using clinical frameworks (OPQRST + SAMPLE).
5. **PDF Report & Destruction**: Answers are compiled into a structured summary downloadable as a PDF — all session data is destroyed when closed.

The whole wizard (landing → 4 form steps → Q&A → summary/PDF, plus the emergency dialog) runs client-side in the browser; the backend owns sessions, the LLM calls and the PDF.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│              PreConsult App                  │
│        (one Cloud Run service :8080)         │
├──────────────────────────┬───────────────────┤
│  React 18 + Vite SPA     │  FastAPI/Starlette│
│  served at /  (web/dist) │  /api + site      │
│  (browser wizard state)  │  (preconsult.host)│
└────────────┬─────────────┴─────────┬─────────┘
             │                       │
             ▼                       ▼
   ┌───────────────────┐   ┌───────────────────┐
   │   Redis Session   │   │ Vertex AI Gemini  │
   │ (30-min Context)  │   │ (Claude on Bedrock│
   │                   │   │  behind the flag) │
   └───────────────────┘   └───────────────────┘
```

The served ASGI app is `src/preconsult/host.py` (`preconsult.host:app`): a Starlette application
wrapping `BotGateMiddleware -> RequestIDMiddleware -> Starlette/GZip`, which mounts the FastAPI
`/api` sub-app first, then `/health*`, the crawler documents (`/robots.txt`, `/sitemap.xml`,
`/llms.txt`), the legal pages (`/privacy`, `/terms`) and finally the SPA at `/`. There is no second
frontend host and no state socket — the wizard's state lives in React, and the session of record
lives in Redis.

---

## Privacy Model

No health data is ever written to disk. Every design decision flows from this constraint:

- **No database** — session state lives in Redis with a 30-minute TTL.
- **No user accounts** — complete anonymity, no registration required.
- **In-memory PDF generation** — reports are built in RAM with ReportLab and streamed directly to the browser.
- **No data in transit to disk** — even if Redis fails, rate limiting falls back to in-memory counters (no clinical data).
- **No browser persistence** — the SPA keeps the wizard in memory and mirrors only the language into the URL; no `localStorage`/`sessionStorage` draft, no API key in the browser.
- **No model training** — API calls use contracts that exclude session data from training.
- **Observability without PHI** — the structured logging layer (`core/observability.py`)
  emits only metadata (event name, request id, language, counts, latencies),
  truncates free-text-derived values and never serializes incident
  complaints/answers; error responses carry stable codes and never include
  exception internals or user data.

## Redis is reserved for real users (free-tier friendly)

PreConsult runs on a **free-tier serverless Redis** (e.g. Upstash) with a finite
daily request quota, so non-user traffic must not consume it. To keep the quota
for actual patient sessions:

- **Nothing opens a Redis connection at import/startup or per health poll.** The app's own
  `session_service` owns real sessions and is the only Redis client in play; adding a framework
  session/token manager, a background keyspace tap or a per-connection ping later is a quota
  regression even when it looks like infrastructure.
- **`/health` and `/health/ready` throttle** their Redis probes (≈1/min) so
  CI, scanners and readiness polling don't hammer storage.
- **The deployed CI smoke test is health/document-only** (stages 1–5: health, the `/` document +
  head contract, the asset graph, the served revision, the legal pages). Full session/stream/
  rate-limit/SSE coverage runs in the `test` job against a local `redis:alpine`; the deployed test
  does not create/read real sessions against production Redis on every push.
- **Analytics are gated to real sessions** — wizard events are only emitted once a
  session exists, so bots that never start the flow can't reach the analytics write
  path.
- **A conservative bot gate** blocks unambiguous scanner/CLI user-agents
  (`curl`, `wget`, `python-requests/urllib`, `go-http-client`, common SEO crawlers)
  on Redis-backed `/api/*` paths with a fast `403` before any storage work. Browsers
  pass through untouched.

**If the quota is ever exhausted, the app degrades gracefully instead of blocking the user.** An
Upstash `max requests limit exceeded` error is classified as `redis_quota_exceeded`: it is
surfaced on `/health` and `/health/ready` (`redis: "quota_exceeded"`, code
`redis_quota_exceeded`) and, when a session genuinely can't be served, returned as a stable
`503 redis_quota_exceeded` on the session/stream/PDF endpoints — distinct from a general
`redis_unavailable` outage, so alerts and ops can tell "daily quota spent" apart from a
connection problem. **Crucially, session create/read/update fall back to the per-worker
in-memory store during a quota outage** (rate-limit/quota already do), so a real user keeps
working through the rest of the quota period; the quota renewal (Upstash free tier resets daily)
is transparent to them.

The in-memory fallback honours the **same 30-minute ephemeral contract** as Redis: each
session copy carries a 30-minute TTL, is pruned lazily on access, and the store is capped
(`_MEMORY_SESSIONS_MAX`, oldest-by-expiry evicted) so a prolonged outage cannot accumulate
unbounded health data in a worker's RAM. Per-worker, in-memory, non-durable, and wiped on
process death — consistent with the product's zero-persistence privacy model.

With low real-user volume this keeps the free tier comfortably within budget.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite 5 (`web/`), built to `web/dist` and served at `/` by the Python host |
| Backend | FastAPI 0.161.1 (`/api` sub-app) inside a Starlette host (`src/preconsult/host.py`), ASGI served by uvicorn |
| Session | Redis (6.4.0, ephemeral, 30-min TTL, signed HttpOnly session cookie, bounded in-memory fallback) |
| AI | Google Vertex AI / Gemini by default, Anthropic Claude Haiku on AWS Bedrock behind `LLM_PROVIDER=bedrock` (needs `uv sync --locked --extra bedrock`; the default image ships Vertex only) |
| PDF | ReportLab 5.1.0 (in-memory, deterministic, localized EN/PT) |
| UI/UX | Glassmorphism, mobile-first, 48px touch targets, prefers-reduced-motion, EN/PT i18n |
| Monitoring | Sentry SDK (2.73.0, PII-safe, env/release-tagged) + structured, PHI-safe request logging + stable error codes + `GET /health`, `/health/live`, `/health/ready`, `/health/metrics` |
| Deployment | GCP Cloud Run, us-central1 (two profiles: `cost_optimized` [default, 0.5 vCPU/1Gi, `min=1`] / `high_performance` [2 vCPU/2Gi, `min=2`], selectable via CI/CD) |
| CI/CD | GitHub Actions (Python tests + Vitest + a Playwright job + WIF auth + Cloud Run deploy) — **exclusive deploy path** (see Deployment section) |

---

## Key Design Decision: Prompt Engineering over RAG

Early versions evaluated ChromaDB and VM-based RAG pipelines. We replaced them with specialized clinical prompt engineering using established frameworks (OPQRST for symptom assessment, SAMPLE for medical history).

Foundation models already contain the necessary medical knowledge. Using a 2026 structured XML prompting architecture (`<role>`, `<clinical_framework>`, `<safety_guardrails>`, `<output_format>`, `<language_setting>`), the system explicitly anchors LLM reasoning to OPQRST/SAMPLE methodologies, adapts intake focus to the requested medical specialty (`{specialist}`), enforces strict non-physician bounds, and triggers emergency red-flag protocols — yielding cleaner, faster, and safer results at a fraction of the infrastructure cost.

---

## Local Setup

The project uses `uv` for the Python side and `npm` for the SPA.

### Prerequisites

- Python 3.11
- Node.js 20+ (for `web/`)
- Redis (via `docker compose` or local install)
- Google Cloud credentials with Vertex AI access (ambient on Cloud Run), or AWS credentials with Bedrock access when `LLM_PROVIDER=bedrock`
- `.env` file in the project root

### Running the App

```bash
docker compose up -d redis
uv sync
uv run uvicorn preconsult.host:app --reload --port 8080   # backend + SPA at http://localhost:8080
```

For frontend work, run Vite's dev server too — it proxies `/api` to the backend on port 8080, so the
HttpOnly session cookie stays same-origin:

```bash
cd web && npm install && npm run dev                     # http://localhost:5173
```

To preview the production layout locally, build the bundle and let the host serve it:

```bash
cd web && npm run build && cd ..
uv run uvicorn preconsult.host:app --port 8080           # serves web/dist at /
```

### Environment Variables

Create a `.env` file:

```bash
PRECONSULT_API_KEY=your_key       # required at startup (unused by the SPA, which is cookie-only)
SESSION_SECRET=your_hex_secret    # required at startup; signs the HttpOnly session cookie
ALLOW_PUBLIC_INIT=true            # the deployed env sets this: the SPA holds no API key
SESSION_COOKIE_SECURE=false       # local plain-HTTP dev only; leave unset (true) in production
AWS_ACCESS_KEY_ID=your_access_key_id        # only for LLM_PROVIDER=bedrock
AWS_SECRET_ACCESS_KEY=your_secret_access_key
LLM_PROVIDER=vertex             # vertex (default) | bedrock
VERTEX_AI_REGION=us-central1
LLM_MODEL=gemini-2.5-flash       # defaults to the provider's model when unset
BEDROCK_REGION=us-east-1        # only read when LLM_PROVIDER=bedrock
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=  # optional
ENV=production             # Sentry environment tag
GIT_SHA=                   # Sentry release tag + log revision tag (injected by CI)
TRUST_PROXY_HEADERS=false  # true on Cloud Run: the peer is the local proxy for every client
TRUST_CF_CONNECTING_IP=false # true only if the domain sits behind Cloudflare's proxy
```

The SPA is built with Vite: `VITE_API_BASE_URL` (optional) is baked in at build time to point the
bundle at another API origin. Leave it unset for same-origin `/api`.

> **Client-IP trust (security):** `get_client_ip` only reads proxy headers when
> `TRUST_PROXY_HEADERS=true`, and then uses the **last** `x-forwarded-for` hop —
> the one our proxy appended — because Cloud Run appends the real client without
> stripping forged prefixes. On Cloud Run this flag must be `true`: the transport
> peer is the local proxy (`169.254.169.126`) for every visitor, so `false` would
> put all users in a single rate-limit and session-quota bucket.
> `cf-connecting-ip` is ignored unless `TRUST_CF_CONNECTING_IP=true`, which is
> only correct behind Cloudflare's proxy (this domain is DNS-only).

> **Bootstrap exception:** `ALLOW_PUBLIC_INIT` defaults to `false`, and the deployed environment sets
> it to `true` because the SPA has no API key — `/api/session/init` must be reachable anonymously to
> mint the cookie. The guards are the per-IP limits (2/min, 20/day), the bot gate and the bounded
> `SessionInitRequest` body; all three are load-bearing.

### Running Tests

```bash
uv sync --locked --extra test
uv run python -m pytest tests/ -v --cov --cov-report=term-missing --cov-fail-under=80
```

The test command enforces an **80% branch-coverage gate** measured over `src/preconsult` only. CI
fails the build if coverage drops below the threshold, and it installs with `uv sync --locked` — a
stale `uv.lock` fails the build instead of silently re-resolving. The SPA has its own suite:

```bash
cd web && npm run lint && npm run test && npm run build
```

The Python suite covers the API (session init, SSE streaming, PDF, quotas, analytics), the SSE
wire-contract, health probes, error handlers with a PHI/data-safety contract, PDF generation, rate
limiting and its in-memory fallback, session CRUD, the shared question/emergency parser, the host
composition (route/middleware order, SPA mount rules), legal pages and SEO documents, i18n/contract
artifact currency, and security (cookie auth, proxy-header trust, HTML sanitization).

#### Browser E2E (Playwright)

One hermetic Playwright job drives the built SPA served by the real backend at `/`, with `/api`
mocked at the browser route layer — no live LLM provider or serverless Redis is needed.

```bash
uv sync --locked --extra e2e
uv run python -m playwright install --with-deps chromium
scripts/run_e2e_spa.sh
```

It asserts the SPA boots at `/`, walks the wizard (landing → steps → streamed questions) and writes
no `localStorage`/`sessionStorage` keys.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | SPA document (React bundle; `no-store` shell, hashed immutable assets) |
| `GET` | `/health` | Aggregate liveness + Redis check (returns `status`, `redis`, `event_channel`) |
| `GET` | `/health/live` | Liveness — process is up, no external dependency probed |
| `GET` | `/health/ready` | Readiness — 200 only when Redis reachable, else 503 with `code: service_unavailable` |
| `GET` | `/health/metrics` | Read-only in-memory counters + served revision (PHI-free) |
| `GET` | `/privacy`, `/terms` | Legal pages from `web/legal/*.html` (`?lang=en|pt`) |
| `GET` | `/robots.txt`, `/sitemap.xml`, `/llms.txt` | Crawler documents |
| `POST` | `/api/session/init` | Create session with full form data (Rate limited: 2/min, 20/day per IP) |
| `POST` | `/api/interview-questions-stream` | SSE stream of LLM-generated clinical questions |
| `POST` | `/api/initial-questions-stream` | SSE stream for initial complaint follow-ups |
| `POST` | `/api/generate-pdf` | Deterministic PDF report from form + Q&A (no LLM call) |
| `POST` | `/api/analytics/event` | Log anonymous funnel analytics event |
| `GET` | `/api/analytics/stats` | 7-day funnel stats |

`/health` reports `event_channel: "not_configured"`: the interactive-channel probe is a per-app
parameter and nothing sets it now that there is no state socket.

> Every error response carries a stable, machine-readable `code`
> (`auth_failed`, `bot_blocked`, `rate_limited`, `session_expired`, `validation_failed`,
> `redis_unavailable`, `redis_quota_exceeded`, `llm_unavailable`,
> `ai_upstream_error`, `service_unavailable`, `internal_error`) alongside the
> human detail, so alerts and CI can key on codes instead of localized text.
> Error responses
> are deliberately generic and never include exception internals or health data.

---

## Deployment (GCP Cloud Run)

> **⚠️ DEPLOYMENT POLICY — MUST FOLLOW**
> The **only** supported way to deploy the serving container is the **GitHub Actions CI/CD** pipeline
> (`.github/workflows/ci-cd.yml`), which builds with `docker buildx` into the `securemed-repo`
> Artifact Registry and deploys via `google-github-actions/deploy-cloudrun`.
>
> **Do NOT use `gcloud run deploy --source .` or any ad-hoc manual rebuild.** Cloud Build's
> `cloud-run-source-deploy` images have proven to be unservable (they return `502` /
> `upstream connect error ... protocol error` even though the process starts). Only CI-built images
> from `securemed-repo` are verified to serve correctly.
>
> **How to deploy:**
> 1. Commit changes and push to `main` — CI auto-deploys on merge.
> 2. Or trigger a manual release: **GitHub Actions → PreConsult CI/CD Pipeline → *Run workflow***.
> 3. To deploy a specific image without rebuilding, use `scripts/deploy_backend.sh [profile] [image_ref]`
>    (this script deploys an **already-built** CI image and never runs `--source`).
>
> Agents (and humans): if the change affects anything the container runs, the change is NOT "done"
> until it has gone through the CI/CD deploy path and the served revision passes a smoke test.
>
> **Scaling & cost:** the default `cost_optimized` profile runs a single worker on a warm
> `--min-instances 1` instance with `--session-affinity`, and `--concurrency 1 --cpu 0.5`.
> **These flags are retained deliberately, not because the app requires them any more.** They date
> from the Reflex era, when an in-memory Engine.IO session store made a recycled instance drop a
> browser's next event; that machinery is gone (the wizard state is in the browser, the session of
> record is in Redis). The only genuinely per-worker state left is the best-effort Redis-outage
> fallback for sessions and rate limits, which is a resilience shim rather than a store of truth.
> The flags stay until a load measurement justifies loosening them (a warm instance also removes
> cold-start latency), and `--concurrency 1` must stay paired with `cpu=0.5` because Cloud Run
> rejects `cpu < 1` when `concurrency > 1`. Instances stay within the `max=5` cap and scale further
> only under load.

### Manual helper (CI-built images only)

```bash
# Deploy the latest CI-built image (default profile: cost_optimized)
scripts/deploy_backend.sh cost_optimized

# Deploy a specific CI-built image by tag/digest
scripts/deploy_backend.sh cost_optimized \
  us-central1-docker.pkg.dev/securemed-chat-494521/securemed-repo/preconsult:<commit-sha>
```

### Custom Domain (Cloudflare DNS → Cloud Run Domain Mapping)

The app is served at **pre-consult.org** via Cloud Run domain mapping. Cloudflare is used as a DNS-only provider (proxy disabled) — DNS A records point to Google's IPs (`216.239.{32,34,36,38}.21`), and Google handles SSL termination. Note: Cloudflare WAF/rate-limit rules and Bot Shield can only take effect if DNS for the domain is actually proxied through Cloudflare; if the apex uses the Google-hosted A records above, they are DNS-only. Any DNS proxy change is a high-risk production change and must be validated against a smoke test after rollout.

Because traffic reaches the service at **Google Frontend** (not through a Cloudflare cache), the served `index.html` shell is served **`no-store`** while its JS/CSS chunks are content-hashed + immutable. A stale cached shell references old chunk URLs that 404 on the current revision, so the app JS never loads and the page stays blank — a stale-document symptom, **not** a server bug (`/health/metrics` and the logs count it as `static.asset_404`). On that error, hard-purge the document and hard-refresh. The CI smoke test asserts the `no-store` document contract, the document head (title, `og:image`, indexable) and the full asset graph resolving 200 (stages 2 & 3).

---

## Project Structure

```
app-preconsult/
├── src/preconsult/             # Python package (the served app)
│   ├── host.py                 # preconsult.host:app — Starlette host: /api, health, site, SPA at /
│   ├── main.py                 # Dev re-export of the hosted app (+ Sentry init)
│   ├── api/
│   │   ├── app.py              # /api FastAPI sub-app + exception-handler registration
│   │   └── endpoints.py        # Routes, SSE streaming, PDF, analytics, get_client_ip
│   ├── core/
│   │   ├── config.py           # Env config, provider selection, cookie/init flags
│   │   ├── errors.py           # Exception handlers, sanitization & stable error codes
│   │   ├── i18n.py             # EN/PT copy (source of truth; exported to contracts/)
│   │   ├── parsing.py          # Shared question/emergency parsing helpers
│   │   ├── llm.py              # LLM client singleton (Vertex default, Bedrock opt-in)
│   │   ├── observability.py    # PHI-safe structured logging & counters
│   │   ├── sentry.py           # PII-safe Sentry init
│   │   └── session_auth.py     # Signed session cookie (mint/verify)
│   ├── services/
│   │   ├── agent_service.py    # LangChain prompts + OPQRST streaming
│   │   ├── pdf_service.py      # In-memory ReportLab PDF generation
│   │   └── session_service.py  # Redis sessions + quota & rate limiting (+ fallbacks)
│   └── site/
│       ├── health.py           # /health, /health/live, /health/ready, /health/metrics
│       ├── legal.py            # /privacy, /terms from web/legal/*.html
│       ├── middleware.py       # BotGateMiddleware
│       ├── request_id.py       # RequestIDMiddleware + outcome counters
│       ├── routes.py           # Wires crawler + legal routes
│       ├── seo.py              # robots.txt / sitemap.xml / llms.txt bodies
│       └── static.py           # SPAStaticFiles: no-store shell, immutable assets
├── web/                        # React 18 + Vite SPA (built into web/dist, served at /)
│   ├── src/
│   │   ├── api/                # client.ts, session.ts, sse.ts, pdf.ts, analytics.ts
│   │   ├── wizard/             # WizardProvider (client-side state) + payload builders
│   │   ├── pages/              # Landing + form steps
│   │   ├── components/         # Header, Stepper, Footer, FAQ, form layout
│   │   ├── i18n/               # I18nProvider (?lang= → navigator.language, URL-only)
│   │   └── contracts/          # Generated artifacts + their tests
│   ├── legal/                  # privacy/terms HTML (en + pt) — the only copy
│   ├── public/                 # og-image and other static assets
│   └── scripts/sync-contracts.mjs
├── contracts/                  # Generated JSON exported from the Python sources
├── scripts/                    # Operational scripts
│   ├── deploy_backend.sh       # Deploy an ALREADY-BUILT CI image (NEVER --source)
│   ├── export_contracts.py     # Regenerate contracts/ from Python sources
│   ├── export_i18n_json.py     # Part of the contract/export pipeline
│   ├── run_e2e_spa.sh          # Build the SPA + run the Playwright specs
│   ├── configure_cloudflare.sh # Cloudflare DNS/WAF/rate-limit configuration
│   ├── run_lighthouse_audit.py # Lighthouse performance audit & JSON/HTML report CLI
│   ├── analyze_cloudrun_logs.py# GCP Cloud Run log fetcher & analyzer
│   ├── analyze_cloudflare_logs.py# Cloudflare HTTP log fetcher & analyzer
│   ├── analyze_week_humans.py  # Weekly human-vs-bot access analysis
│   ├── analyze_all_logs.py     # Unified logs analysis script
│   └── setup_wif.sh            # Workload Identity Federation setup
├── tests/                      # Python suite (80% branch-coverage gate) + tests/e2e_spa
├── AGENTS.md                   # Agent rules (incl. CI/CD-only deploy policy)
├── Dockerfile                  # Multi-stage container build
├── docker-compose.yml          # Local Redis service
├── pyproject.toml              # Dependencies, build config & coverage gate
└── .github/workflows/ci-cd.yml
```

---

## UX Principles

The UI is built around three core design principles:

- **Mobile-first**: 48px minimum touch targets, generous padding (16px+), and responsive layouts optimized for mobile devices.
- **Privacy as trust**: Persistent privacy badges and notices throughout intake, Privacy Policy & Terms of Service pages, and clear zero-retention assurances.
- **Accessibility & Safety**: Minimum 16px font sizes, support for `prefers-reduced-motion`, high-contrast error callouts, loading skeletons, and interactive Emergency Warning dialogues.

---

> **Disclaimer**: PreConsult is an organizational tool designed to assist patients in organizing symptom information prior to medical consultations. It does not provide medical diagnoses, treatment recommendations, or emergency services. Always consult a qualified healthcare provider for medical advice.
