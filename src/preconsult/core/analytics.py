"""Funnel event contract.

The event names are the contract between the SPA and
``POST /api/analytics/event``. They live here — not in the endpoint and not in
the TypeScript — because ``scripts/export_contracts.py`` emits them to
``contracts/funnel_events.json`` and ``web/scripts/sync-contracts.mjs`` turns
that into a typed module, so the two sides cannot drift.

The split is a storage decision, not a taxonomy:

* ``ANONYMOUS_FUNNEL_EVENTS`` run before the session exists (it is created at
  the lifestyle step). They are counted in memory and logged, never written to
  Redis, which is reserved for real patient sessions.
* ``SESSION_FUNNEL_EVENTS`` are the 7-day Redis funnel and stay gated on a
  session id.
"""

ANONYMOUS_FUNNEL_EVENTS: tuple[str, ...] = (
    "intake_started",
    "demographics_submitted",
    "complaint_submitted",
    "history_submitted",
)

SESSION_FUNNEL_EVENTS: tuple[str, ...] = (
    "lifestyle_submitted",
    "summary_generated",
    "pdf_downloaded",
)

FUNNEL_EVENTS: tuple[str, ...] = ANONYMOUS_FUNNEL_EVENTS + SESSION_FUNNEL_EVENTS
