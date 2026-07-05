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
- **High-Performance State** — uses Redis Hashes for granular, partial updates, minimizing I/O and latency.
- **Local API Routing** — the UI communicates with the API on the same origin (no cross-service exposure).
- **No model training** — API calls use contracts that exclude session data from training.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Core | Reflex (Unified Frontend & API Host) |
| Backend | FastAPI (Integrated into Reflex backend) |
| Session | Redis (Hashes, ephemeral, 30-min TTL) |
| AI | Vertex AI (Gemini-Flash) |
| Deployment | GCP Cloud Run (1.0 CPU, 1Gi RAM, Scale-to-Zero) |
| CI/CD | GitHub Actions (Consolidated Mono-Service build) |

---

## Key Design Decision: Prompt Engineering over RAG

Early versions used ChromaDB and a VM-based RAG pipeline. We replaced it with specialized clinical prompt engineering using established frameworks (OPQRST for symptom assessment, SAMPLE for medical history).

Foundation models already contain the necessary medical knowledge. Structured prompting yields cleaner, faster results at a fraction of the infrastructure cost — eliminating ~$100/month in cloud spend.

---

## Local Setup

The project uses `uv` for lightning-fast dependency management.

### Running the App
1. **Start infrastructure** (Redis):
   ```bash
   docker compose up -d redis
   ```

2. **Start the Unified App**:
   ```bash
   # Both UI and API will run together
   uv run reflex run
   ```

Requires a `.env` file in the root with:
```bash
PRECONSULT_API_KEY=your_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### Running Tests
The project includes a comprehensive suite of 34 tests covering services, security, and integration.

```bash
# Sync test dependencies
uv sync --extra test

# Run full suite
uv run python -m pytest tests/
```

---

## Deployment (GCP Cloud Run)

The app is deployed as a single consolidated container:

```bash
gcloud run deploy preconsult \
  --source . \
  --project=securemed-chat-494521 \
  --region=southamerica-east1 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --set-secrets=PRECONSULT_API_KEY=PRECONSULT_API_KEY:latest,REDIS_URL=REDIS_URL:latest
```

### Custom Domain & Routing (Cloudflare)

Because legacy domain mappings are not supported in the GCP `southamerica-east1` region, the app uses **pre-consult.org** mapped via a **Cloudflare Worker** to route traffic and rewrite the `Host` header on the fly. 

To update or manage this:
- The compiled React/Next.js frontend in the container uses `https://pre-consult.org` as its target `API_URL`.
- Incoming traffic to `https://pre-consult.org` is proxied via a Cloudflare Worker that forwards requests to the GCP Cloud Run service endpoint (`preconsult-811607528687.southamerica-east1.run.app`) while rewriting the `Host` header to match.

---

> **Disclaimer**: PreConsult is an organizational tool, not a medical device. It does not provide diagnoses or medical advice. Always consult a qualified healthcare provider.
