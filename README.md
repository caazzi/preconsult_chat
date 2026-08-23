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

---

## Architecture

```
┌──────────────────────────────────────────┐
│             PreConsult App               │
│       (Unified Cloud Run Service)        │
├────────────────────┬─────────────────────┤
│     Reflex UI      │   FastAPI Backend   │
│  (React/Next.js)   │  (Interview/PDF)    │
└─────────┬──────────┴──────────┬──────────┘
          │                     │
          ▼                     ▼
┌───────────────────┐ ┌───────────────────┐
│   Redis Session   │ │    Vertex AI      │
│ (30-min Context)  │ │ (Clinical LLM)    │
└───────────────────┘ └───────────────────┘
```

---

## Privacy Model

No health data is ever written to disk. Every design decision flows from this constraint:

- **No database** — session state lives in Redis with a 30-minute TTL.
- **No user accounts** — complete anonymity, no registration required.
- **In-memory PDF generation** — reports are built in RAM with ReportLab and streamed directly to the browser.
- **No data in transit to disk** — even if Redis fails, rate limiting falls back to in-memory counters (no clinical data).
- **No model training** — API calls use contracts that exclude session data from training.
- **Observability without PHI** — the structured logging layer (`core/observability.py`)
  emits only metadata (event name, request id, language, counts, latencies),
  truncates free-text-derived values and never serializes incident
  complaints/answers; error responses carry stable codes and never include
  exception internals or user data.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Core | Reflex 0.9.6 (Unified Frontend & API Host) |
| Backend | FastAPI (0.136.1, integrated into Reflex backend) |
| Session | Redis (6.4.0, ephemeral, 30-min TTL, in-memory fallback for rate limiting) |
| AI | Vertex AI Gemini 2.5 Flash Lite (`langchain-google-vertexai` 2.1.2) |
| PDF | ReportLab 5.0.0 (in-memory, deterministic, localized EN/PT) |
| UI/UX | Glassmorphism, mobile-first, 48px touch targets, prefers-reduced-motion, EN/PT i18n |
| Monitoring | Sentry SDK (2.65.0, PII-safe, env/release-tagged) + structured, PHI-safe request logging + stable error codes + `GET /health`, `/health/live`, `/health/ready` |
| Deployment | GCP Cloud Run, us-central1 (two profiles: `high_performance` / `standard`, selectable via CI/CD) |
| CI/CD | GitHub Actions (tests + WIF auth + Cloud Run deploy) — **exclusive deploy path** (see Deployment section) |

---

## Key Design Decision: Prompt Engineering over RAG

Early versions evaluated ChromaDB and VM-based RAG pipelines. We replaced them with specialized clinical prompt engineering using established frameworks (OPQRST for symptom assessment, SAMPLE for medical history).

Foundation models already contain the necessary medical knowledge. Using a 2026 structured XML prompting architecture (`<role>`, `<clinical_framework>`, `<safety_guardrails>`, `<output_format>`, `<language_setting>`), the system explicitly anchors LLM reasoning to OPQRST/SAMPLE methodologies, adapts intake focus to the requested medical specialty (`{specialist}`), enforces strict non-physician bounds, and triggers emergency red-flag protocols — yielding cleaner, faster, and safer results at a fraction of the infrastructure cost.

---

## Local Setup

The project uses `uv` for fast dependency management.

### Prerequisites

- Python 3.11
- Redis (via `docker compose` or local install)
- GCP service account with Vertex AI access
- `.env` file in the project root

### Running the App

```bash
docker compose up -d redis
uv sync
uv run reflex run
```

### Environment Variables

Create a `.env` file:

```bash
PRECONSULT_API_KEY=your_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
GOOGLE_CLOUD_PROJECT=your_project_id
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=  # optional
GTAG_ID=     # optional
TRUST_PROXY_HEADERS=false  # enable only when behind a trusted fronting proxy
ENV=production             # Sentry environment tag
GIT_SHA=                   # Sentry release tag (injected by CI)
```

> **Client-IP trust (security):** `get_client_ip` honors `cf-connecting-ip` /
> `x-forwarded-for` only when `TRUST_PROXY_HEADERS=true`. Leave it `false`
> (default) unless requests actually traverse a trusted proxy — otherwise a
> spoofed header lets a client rotate IPs and bypass per-IP rate limits / quotas.

### Running Tests

```bash
uv sync --extra test
uv run python -m pytest tests/ -v --cov --cov-report=term-missing --cov-fail-under=80
```

The test command enforces an **80% coverage gate** (measured over `src/preconsult`
and `reflex_app/preconsult`, branch coverage, excluding the declarative Reflex
page tree). CI fails the build if coverage drops below the threshold.

The test suite contains **199 tests, one skipped**, with **~85% overall coverage**
(branch coverage, measured over `src/preconsult` and `reflex_app/preconsult`,
excluding the generated Reflex page tree). Coverage is broken down as:
`errors.py` and `core/parsing.py` 100%, `llm.py` 100%, `endpoints.py` 94%,
`pdf_service.py` 90%, `session_service.py` 86%, `state.py` 84%,
`observability.py` 94%.

Current categories:
- **State machine (Reflex)**: step transitions & validation, session-init payload
  construction, SSE question-stream parsing (incl. emergency red-flag,
  timeout and error branches), answer summary building, PDF download flow,
  `detect_lang`, `AdminState` token gating.
- **Agent Service**: XML prompt structure, OPQRST & SAMPLE frameworks,
  multi-language formatting, emergency condition detection.
- **API Integration**: session init, SSE streaming, PDF generation, quotas &
  analytics endpoints, **SSE wire-contract** (exact `data:` format the client
  consumes), and **health probe split** (`/health`, `/health/live`, `/health/ready`).
- **Error handlers & privacy**: every exception handler driven directly, stable
  machine-readable `code`s, and a **PHI/data-safety contract** asserting error
  responses never leak exception internals or user-supplied values.
- **PDF Generation**: localized ReportLab layouts, pagination, wrapped text,
  empty/missing-field resilience.
- **Rate Limiting & Quotas**: Redis-backed (Lua `EVAL`) and in-memory fallback
  paths, concurrent creation locks, deterministic global-state reset.
- **Security**: API key enforcement, proxy-header trust policy for client IP,
  HTML sanitization, `BUILD_MODE` bypass.
- **Observability**: PHI-safe structured logging, structured value truncation,
  and resilience (logging failures never break the request path).
- **Session Service**: ephemeral CRUD and automatic recovery on Redis reconnect.
- **Reflex frontend / i18n / parsing**: component rendering, wizard transitions,
  language switcher, bot scanner, Privacy & Terms routing, question parser.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root — welcome message |
| `GET` | `/health` | Aggregate liveness + Redis check (returns `status` + `redis`) |
| `GET` | `/health/live` | Liveness — process is up, no external dependency probed |
| `GET` | `/health/ready` | Readiness — 200 only when Redis reachable, else 503 with `code: service_unavailable` |
| `POST` | `/api/session/init` | Create session with full form data (Rate limited: 2/min, 20/day per IP) |
| `POST` | `/api/interview-questions-stream` | SSE stream of LLM-generated clinical questions |
| `POST` | `/api/initial-questions-stream` | SSE stream for initial complaint follow-ups |
| `POST` | `/api/generate-pdf` | Deterministic PDF report from form + Q&A (no LLM call) |
| `POST` | `/api/analytics/event` | Log anonymous funnel analytics event |
| `GET` | `/api/analytics/stats` | 7-day funnel stats |

> Every error response carries a stable, machine-readable `code`
> (`auth_failed`, `rate_limited`, `session_expired`, `validation_failed`,
> `redis_unavailable`, `llm_unavailable`, `ai_upstream_error`,
> `service_unavailable`, `internal_error`) alongside the human detail, so
> alerts and CI can key on codes instead of localized text. Error responses
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

---

## Project Structure

```
app-preconsult/
├── src/preconsult/          # FastAPI Backend package
│   ├── api/endpoints.py     # FastAPI routes & SSE streaming
│   ├── core/config.py       # Environment config & secrets (incl. TRUST_PROXY_HEADERS)
│   ├── core/errors.py       # Exception handlers, sanitization & error codes
│   ├── core/observability.py# PHI-safe structured logging & request ids
│   ├── core/parsing.py      # Shared question/emergency parsing helpers
│   ├── core/llm.py          # Vertex AI Gemini singleton
│   ├── main.py              # FastAPI app + Sentry + health check
│   └── services/
│       ├── agent_service.py  # LangChain prompts + OPQRST streaming
│       ├── pdf_service.py    # In-memory ReportLab PDF generation
│       └── session_service.py# Redis state + quota & rate limiting
├── reflex_app/preconsult/   # Reflex Frontend
│   ├── preconsult.py        # UI components, wizard flow, modals & health routes
│   ├── state.py             # Reflex state management & API streaming
│   ├── analytics.py         # HTTP event tracking
│   └── i18n.py              # EN/PT translations & legal content
├── scripts/                 # Utility & Operations Scripts
│   ├── deploy_backend.sh     # Deploy an ALREADY-BUILT CI image (NEVER --source)
│   ├── configure_cloudflare.sh# Cloudflare DNS/WAF/rate-limit configuration
│   ├── run_lighthouse_audit.py# Lighthouse performance audit & JSON/HTML report CLI
│   ├── analyze_cloudrun_logs.py# GCP Cloud Run log fetcher & analyzer
│   ├── analyze_cloudflare_logs.py# Cloudflare HTTP log fetcher & analyzer
│   ├── analyze_week_humans.py# Weekly human-vs-bot access analysis
│   └── analyze_all_logs.py  # Unified logs analysis script
├── tests/                   # 199 tests; 80% coverage gate
├── AGENTS.md                # Agent rules (incl. CI/CD-only deploy policy)
├── Dockerfile               # Multi-stage container build
├── docker-compose.yml       # Local Redis service
├── pyproject.toml           # Dependencies, build config & coverage gate
└── .github/workflows/ci-cd.yml
```

---

## UX Principles

The UI is built around three core design principles:

- **Mobile-first**: 48px minimum touch targets, generous padding (16px+), and responsive layouts optimized for mobile devices.
- **Privacy as trust**: Persistent privacy badges and notices throughout intake, Privacy Policy & Terms of Service modals, and clear zero-retention assurances.
- **Accessibility & Safety**: Minimum 16px font sizes, support for `prefers-reduced-motion`, high-contrast error callouts, loading skeletons, and interactive Emergency Warning dialogues.

---

> **Disclaimer**: PreConsult is an organizational tool designed to assist patients in organizing symptom information prior to medical consultations. It does not provide medical diagnoses, treatment recommendations, or emergency services. Always consult a qualified healthcare provider for medical advice.
