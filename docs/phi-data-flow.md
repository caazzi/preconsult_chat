# PHI Data Flow — PreConsult

The product's central promise is **zero persistence of health data**. This map
states, per surface, what PHI can exist, for how long, and where it must never
go. PHI = chief complaint, complaint detail, conditions, medications,
allergies, family history, lifestyle answers, and the Q&A pairs.

## Where PHI exists

| Surface | Contains PHI? | Lifetime | Notes |
|---|---|---|---|
| Request body (HTTPS/TLS) | Yes | in flight | e.g. `session/init` form, Q&A for PDF |
| Server session store (Redis / in-memory shim) | Yes | 30-min TTL | capped `_MEMORY_SESSIONS_MAX`, oldest evicted |
| LLM call (`LLM_PROVIDER`: Vertex Gemini by default, Bedrock Claude Haiku when selected) | Chief complaint + structured form | request-scoped | The patient's free-text **answers never return to the LLM** (PRD §3.4). Provider not retained/trained per its enterprise terms. |
| Server logs (`core/observability.py`) | **No** | — | metadata only (event, request id, lang, counts, durations); free-text values never serialized, only `len(...)` |
| Error responses (`core/errors.py`) | **No** | — | generic localized detail + stable `code`; never exception internals or user values |
| Browser client store (SPA) | Yes (in memory) | tab session | **No** `localStorage`/`sessionStorage` persistence (`TestP9` guard), and the language is mirrored into `?lang=` only (no cookie written) |
| Session cookie (`preconsult_session`) | **No** | session (dropped on close) | signed **opaque session id** only; HttpOnly, Secure, SameSite=Strict, no Max-Age |
| PDF report | Yes | client-only | built in memory (ReportLab) and streamed to the browser; never written to disk |
| Analytics counters (Redis) | **No** | 30 days | anonymous event-key increments only |

## Rules (regression-guarded)

1. **Never log or serialize PHI.** Only metadata; lengths, not values.
   (`tests/test_observability.py`, `tests/test_error_handlers.py`)
2. **Never persist PHI client-side.** No `localStorage`/`sessionStorage` draft.
   (`tests/test_security.py::TestP9_NoPHIDraftPersistence`)
3. **Never put PHI in the cookie.** The cookie is a signed session id only.
   (`tests/test_session_auth.py`)
4. **The LLM sees only the pre-answers form**, never the patient's Q&A answers.
5. **Errors never leak incident data** or exception internals.
   (`tests/test_error_handlers.py`)
6. **Ephemeral everywhere:** Redis TTL 30 min, in-memory shim same TTL + cap,
   session cookie dropped on close, no database.

## Third parties

| Provider | Data | Posture |
|---|---|---|
| Google Vertex AI (default) / AWS Bedrock (opt-in) | chief complaint + structured form | not retained, not used for training |
| Upstash Redis / in-memory | session PHI | 30-min TTL; in-memory fallback honored on outage |
| Sentry | metadata only (`send_default_pii=False`) | release/env tagged, PHI-free |

## Sources of truth

- Policy copy: `web/legal/*.html` (`privacy.{en,pt}.html`, `terms.{en,pt}.html`)
  served by `src/preconsult/site/legal.py`, and the UI copy in
  `src/preconsult/core/i18n.py`.
- Enforcement: `core/observability.py`, `core/errors.py`, `core/session_auth.py`,
  `services/session_service.py`, `site/middleware.py` (bot gate) and
  `site/request_id.py` (PHI-safe request logging/counters).
- Product spec: `docs/PRD.md` §3 (principles) and §3.4 (single LLM call).
