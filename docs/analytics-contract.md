# Analytics Funnel — Event-Key Contract

The frontend emits anonymous funnel events to `POST /api/analytics/event`
(`{ "event": "<key>" }`). This document is the authoritative list of keys, their
trigger points, and how they map to the 7-day funnel returned by
`GET /api/analytics/stats`.

Any frontend rewrite must emit exactly these keys. Do not invent new ones; to
add a step, extend this document, the funnel aggregation in
`src/preconsult/api/endpoints.py`, and the corresponding sources below.

---

## Event keys & trigger points

Emitted from the SPA via `logEvent` in `web/src/api/analytics.ts`; call sites live
in the wizard provider (`web/src/wizard/WizardProvider.tsx`).

| Event key | Trigger point |
|---|---|
| `intake_started` | User starts the flow from the landing page. |
| `demographics_submitted` | User completes the demographics step. |
| `complaint_submitted` | User completes the chief-complaint step. |
| `history_submitted` | User completes the medical-history step. |
| `lifestyle_submitted` | A session is created and the question stream starts. |
| `summary_generated` | User submits the Q&A to build the summary. |
| `pdf_downloaded` | User downloads the PDF report. |

## Two storage tiers (privacy / Redis budget)

The session is created at the **lifestyle** step, so the four steps before it have
no `session_id` to key on. Splitting by tier is what makes the top of the funnel
observable at all — a single "no session, no event" rule silently zeroed the
first four rungs.

| Step keys | Recorded in | Needs a session? |
|---|---|---|
| `intake_started`, `demographics_submitted`, `complaint_submitted`, `history_submitted` | in-memory counter `funnel.<key>` (read via `GET /health/metrics`) + one `funnel.step` log line | no |
| `lifestyle_submitted`, `summary_generated`, `pdf_downloaded` | Redis hash `analytics:<date>` (`GET /api/analytics/stats`) | yes |

- The split is enforced **server-side** (`ANONYMOUS_FUNNEL_EVENTS` in
  `src/preconsult/api/endpoints.py`), and the request model is a `Literal`
  whitelist — a client cannot invent a key or grow the free-tier Redis hash.
- Pre-session steps **never touch Redis**: the serverless quota stays reserved for
  real patient sessions.
- `logEvent` (`web/src/api/analytics.ts`) still refuses to send a **session** key
  without a `session_id`, so bots and early exits cannot reach the write path.
- Both tiers are PHI-free: a stable event name and a counter, nothing else.
- `/health/metrics` counters are per-worker and reset when the revision restarts;
  the `funnel.step` log lines are the persistent history.

## Mapping to `GET /api/analytics/stats`

The 7-day stats endpoint aggregates daily counters by the event key, e.g.
`funnel[day]["demographics"] = count of "demographics_submitted"`. Key → field:

| Funnel field | Source event key |
|---|---|
| `demographics` | `demographics_submitted` |
| `complaint` | `complaint_submitted` |
| `history` | `history_submitted` |
| `lifestyle` | `lifestyle_submitted` |
| `summary` | `summary_generated` |
| `pdf` | `pdf_downloaded` |

> `intake_started` is recorded (in memory / logs, see the tiers above) but does
> not appear as its own field here — the 7-day Redis funnel starts at
> `demographics`. `date` is the bucket's ISO date.

## Sources of truth

- Emitters: `web/src/api/analytics.ts` (`logEvent`, keyed by the `FunnelEvent`
  union) and its call sites in `web/src/wizard/WizardProvider.tsx`
- Ingest: `src/preconsult/api/endpoints.py::log_analytics_event` +
  `AnalyticsEventRequest`
- Aggregation: `src/preconsult/api/endpoints.py::get_analytics_stats`
- HTTP surface: `docs/api-contract.md` (auth, rate limits)
