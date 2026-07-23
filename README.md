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
| Monitoring | Sentry SDK (2.65.0) + `GET /health` endpoint |
| Deployment | GCP Cloud Run (1.0 CPU, 1Gi RAM, 0-5 instances) |
| CI/CD | GitHub Actions (tests + WIF auth + Cloud Run deploy) |

---

## Key Design Decision: Prompt Engineering over RAG

Early versions evaluated ChromaDB and VM-based RAG pipelines. We replaced them with specialized clinical prompt engineering using established frameworks (OPQRST for symptom assessment, SAMPLE for medical history).

Foundation models already contain the necessary medical knowledge. Structured prompting yields cleaner, faster results at a fraction of the infrastructure cost — eliminating unnecessary database overhead and cloud spend.

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
```

### Running Tests

```bash
uv sync --extra test
uv run python -m pytest tests/ -v
```

The test suite contains **104 passing tests** covering:
- **Agent Service**: LLM chains, multi-language prompt formatting, emergency condition detection.
- **API Integration**: Session initialization, SSE question streaming, PDF generation, daily quotas & analytics endpoints.
- **PDF Generation**: Localized ReportLab layouts, pagination, wrapped text, empty/missing field resilience.
- **Rate Limiting & Quotas**: Redis-backed limits, fallback memory counters, concurrent creation locks.
- **Security**: API key enforcement, HTML input sanitization, error response stripping, `BUILD_MODE` bypass tests.
- **Session Service**: Ephemeral storage CRUD operations and automatic recovery upon Redis reconnection.
- **Reflex Frontend & i18n**: Component rendering, multi-step state transitions, language switcher, bot scanner blocking, Privacy & Terms modal routing.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root — welcome message |
| `GET` | `/health` | Liveness & readiness probe (returns status + Redis check) |
| `POST` | `/api/session/init` | Create session with full form data (Rate limited: 2/min, 20/day per IP) |
| `POST` | `/api/interview-questions-stream` | SSE stream of LLM-generated clinical questions |
| `POST` | `/api/initial-questions-stream` | SSE stream for initial complaint follow-ups |
| `POST` | `/api/generate-pdf` | Deterministic PDF report from form + Q&A (no LLM call) |
| `POST` | `/api/analytics/event` | Log anonymous funnel analytics event |
| `GET` | `/api/analytics/stats` | 7-day funnel stats |

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

The app is served at **pre-consult.org** via Cloudflare Worker proxying to Cloud Run with `Host` header rewriting.

---

## Project Structure

```
app-preconsult/
├── src/preconsult/          # FastAPI Backend package
│   ├── api/endpoints.py     # FastAPI routes & SSE streaming
│   ├── core/config.py       # Environment config & secrets
│   ├── core/errors.py       # Exception handlers & error sanitization
│   ├── core/llm.py          # Vertex AI Gemini singleton
│   ├── main.py              # FastAPI app + Sentry + health check
│   └── services/
│       ├── agent_service.py  # LangChain prompts + OPQRST streaming
│       ├── pdf_service.py    # In-memory ReportLab PDF generation
│       └── session_service.py# Redis state + quota & rate limiting
├── reflex_app/preconsult/   # Reflex Frontend
│   ├── preconsult.py        # UI components, wizard flow & modals
│   ├── state.py             # Reflex state management & API streaming
│   ├── analytics.py         # HTTP event tracking
│   └── i18n.py              # EN/PT translations & legal content
├── tests/                   # 104 tests
├── Dockerfile               # Multi-stage container build
├── docker-compose.yml       # Local Redis service
├── pyproject.toml           # Dependencies & build configuration
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
