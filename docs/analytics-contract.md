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

## Real-session gating (privacy/Redis budget)

- **`logEvent` is a no-op until a real session exists** (empty `sessionId` returns
  immediately). Bots / early-exit visitors that never start the session flow must
  not reach the analytics Redis write path — this protects the serverless Redis
  quota and the zero-persistence privacy model.
- The gating rule lives in `web/src/api/analytics.ts::logEvent` and is documented
  in `AGENTS.md` ("Analytics are gated on a real session").
- A rewrite must preserve this: **never fire a funnel event without a
  `session_id`.**

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

> `intake_started` is recorded but does not appear as its own funnel field
> (the funnel starts at `demographics`). `date` is the bucket's ISO date.

## Sources of truth

- Emitters: `web/src/api/analytics.ts` (`logEvent`, keyed by the `FunnelEvent`
  union) and its call sites in `web/src/wizard/WizardProvider.tsx`
- Ingest: `src/preconsult/api/endpoints.py::log_analytics_event` +
  `AnalyticsEventRequest`
- Aggregation: `src/preconsult/api/endpoints.py::get_analytics_stats`
- HTTP surface: `docs/api-contract.md` (auth, rate limits)
