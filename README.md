# PreConsult — Privacy-First Medical Intake Assistant

An AI-powered web app that helps patients organize their symptoms before a doctor's visit. The core design constraint: **zero data persistence** — no database, no user accounts, no logs containing health data.

---

## The Problem

Patients arrive at consultations anxious and forget key details. Doctors have limited time. The gap between what the patient knows and what the doctor hears costs both sides.

PreConsult bridges that gap with a guided AI interview that generates a structured clinical summary — then destroys all data when the session ends.

---

## How It Works

1. Patient enters their specialty and chief complaint in plain text
2. The AI generates 3–5 targeted follow-up questions using clinical frameworks (OPQRST + SAMPLE)
3. Answers are compiled into a structured summary the patient can download as a PDF
4. Session data is destroyed — nothing is retained on the server

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
- **In-memory PDF generation** — reports are built in RAM and streamed directly to the browser.
- **No data in transit to disk** — even if Redis fails, rate limiting falls back to in-memory counters (no clinical data).
- **No model training** — API calls use contracts that exclude session data from training.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Core | Reflex 0.9.1 (Unified Frontend & API Host) |
| Backend | FastAPI (Integrated into Reflex backend) |
| Session | Redis (Hashes, ephemeral, 30-min TTL, RedisUnavailable → 503) |
| AI | Vertex AI Gemini 2.5 Flash Lite (via LangChain) |
| PDF | ReportLab (in-memory, deterministic, no LLM call) |
| Monitoring | Sentry (error tracking) + `GET /health` endpoint |
| Deployment | GCP Cloud Run (1.0 CPU, 1Gi RAM, 0-5 instances) |
| CI/CD | GitHub Actions (tests + WIF auth + Cloud Run deploy) |

---

## Key Design Decision: Prompt Engineering over RAG

Early versions used ChromaDB and a VM-based RAG pipeline. We replaced it with specialized clinical prompt engineering using established frameworks (OPQRST for symptom assessment, SAMPLE for medical history).

Foundation models already contain the necessary medical knowledge. Structured prompting yields cleaner, faster results at a fraction of the infrastructure cost — eliminating ~$100/month in cloud spend.

---

## Local Setup

The project uses `uv` for dependency management.

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
```

### Running Tests

```bash
uv sync --extra test
uv run python -m pytest tests/ -v
```

The suite has **50 tests** covering:
- Agent service (LLM chains, language, emergency detection)
- API integration (session init, streaming, PDF generation, analytics)
- PDF generation (i18n, pagination, empty states)
- Rate limiting (Redis + in-memory fallback, concurrency)
- Security (API key enforcement, error sanitization, BUILD_MODE)
- Session service (CRUD, Redis recovery after failure)
- i18n (fallback, key consistency, `get_localized_value`)

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root — welcome message |
| `GET` | `/health` | Liveness probe (returns `{"status": "healthy", "redis": "ok"}`) |
| `POST` | `/api/session/init` | Create session with full form data (rate limited: 2/min) |
| `POST` | `/api/interview-questions-stream` | SSE stream of LLM-generated clinical questions |
| `POST` | `/api/generate-pdf` | Deterministic PDF from form + Q&A (no LLM call) |
| `POST` | `/api/analytics/event` | Log analytics event |
| `GET` | `/api/analytics/stats` | 7-day funnel stats (token-gated) |

---

## Deployment (GCP Cloud Run)

The app deploys as a single consolidated container via GitHub Actions CI/CD.

### Manual deploy

```bash
gcloud run deploy preconsult \
  --source . \
  --project=securemed-chat-494521 \
  --region=southamerica-east1 \
  --memory=1Gi --cpu=1 \
  --min-instances=0 --max-instances=5 \
  --concurrency=80 \
  --set-secrets=PRECONSULT_API_KEY=PRECONSULT_API_KEY:latest,REDIS_URL=REDIS_URL:latest
```

### Custom Domain (Cloudflare)

The app is served at **pre-consult.org** via a Cloudflare Worker that proxies requests to the Cloud Run endpoint, rewriting the `Host` header to match GCP's requirements.

---

## Project Structure

```
preconsult_chat/
├── src/preconsult/          # Backend package
│   ├── api/endpoints.py     # FastAPI routes
│   ├── core/config.py       # Environment config
│   ├── core/errors.py       # Exception handlers
│   ├── core/llm.py          # Vertex AI singleton
│   ├── main.py              # FastAPI app + Sentry + health
│   └── services/
│       ├── agent_service.py  # LangChain prompts + streaming
│       ├── pdf_service.py    # ReportLab PDF generation
│       └── session_service.py# Redis + in-memory rate limiting
├── reflex_app/preconsult/   # Reflex frontend
│   ├── preconsult.py        # UI components + app setup
│   ├── state.py             # Reflex state + API calls
│   ├── analytics.py         # Analytics via HTTP
│   └── i18n.py              # EN/PT translations (174 keys)
├── tests/                   # 50 tests
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Local Redis
└── .github/workflows/ci-cd.yml
```

---

## Phases Completed

| Phase | Focus | Commits |
|---|---|---|
| 0 | Security: race condition, API_BASE_URL, BUILD_MODE, Sentry | 1 |
| 1 | Resilience: Redis fallback, error handlers, sanitized errors, analytics HTTP | 2 |
| 1.5 | Test coverage: mock cleanup, 7 new tests | 1 |
| 2 | Maintenance: gender-neutral, PDF i18n, Dependabot | 1 |
| 3 | Coverage: concurrency tests, i18n edge cases | 1 |
| 4 | Infra: healthcheck, MockWebSocket extraction | 1 |
| 5 | UI/UX: mobile-first layout, inline errors via callout, streaming timeout | 2 |
| | **Total** | **50 tests, ~68% coverage** |

---

> **Disclaimer**: PreConsult is an organizational tool, not a medical device. It does not provide diagnoses or medical advice. Always consult a qualified healthcare provider.
