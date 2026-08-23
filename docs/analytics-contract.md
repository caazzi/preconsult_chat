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

Emitted from `reflex_app/preconsult/state.py` (via `State.log_analytics_event`).

| Event key | Trigger point |
|---|---|
| `intake_started` | User clicks the landing CTA to start the flow (`start_intake`). |
| `demographics_submitted` | User completes the demographics step (`go_to_step_2`). |
| `complaint_submitted` | User completes the chief-complaint step (`go_to_step_3`). |
| `history_submitted` | User completes the medical-history step (`go_to_step_4`). |
| `lifestyle_submitted` | A session is created (`init_session` OK, `go_to_step_5`). |
| `summary_generated` | User submits Q&A to build the summary (`submit_answers`). |
| `pdf_downloaded` | User downloads the PDF report (`download_report`). |

## Real-session gating (privacy/Redis budget)

- **`log_analytics_event` is a no-op until a real session exists** (`session_id`
  is set). Bots / early-exit visitors that never start the session flow must not
  reach the analytics Redis write path — this protects the serverless Redis
  quota and the zero-persistence privacy model.
- The gating rule lives in `state.py::log_analytics_event` and is documented in
  `AGENTS.md` ("Analytics are gated to real sessions").
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

- Emitters: `reflex_app/preconsult/state.py` (`log_analytics_event`, `start_intake`,
  `go_to_step_2/3/4`, `init_session`, `submit_answers`, `download_report`)
- Ingest: `src/preconsult/api/endpoints.py::log_analytics_event` +
  `AnalyticsEventRequest`
- Aggregation: `src/preconsult/api/endpoints.py::get_analytics_stats`
- HTTP surface: `docs/api-contract.md` (auth, rate limits)
