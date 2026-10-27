// Funnel analytics. Event keys are pinned by docs/analytics-contract.md and
// must match the backend whitelist exactly.
//
// TWO TIERS, and the difference is a Redis-budget decision:
//   - Pre-session steps (intake_started .. history_submitted) happen before a
//     session exists. The server counts them in RAM and logs them, so they are
//     allowed without a session id and never touch Redis.
//   - Session steps (lifestyle_submitted, summary_generated, pdf_downloaded) are
//     the 7-day Redis funnel and stay gated on a real session, so bots and
//     early exits cannot reach the write path.

import { apiFetch } from "./client";

export type FunnelEvent =
  | "intake_started"
  | "demographics_submitted"
  | "complaint_submitted"
  | "history_submitted"
  | "lifestyle_submitted"
  | "summary_generated"
  | "pdf_downloaded";

/** Events recorded in Redis, and therefore gated on a real session. */
const SESSION_GATED_EVENTS: readonly FunnelEvent[] = [
  "lifestyle_submitted",
  "summary_generated",
  "pdf_downloaded",
];

/**
 * Fire-and-forget funnel event. Session-gated keys are a no-op without a
 * `sessionId`; pre-session steps are allowed anonymously. Never throws —
 * analytics must not break the user flow.
 */
export function logEvent(event: FunnelEvent, sessionId = ""): void {
  if (SESSION_GATED_EVENTS.includes(event) && !sessionId) return;
  void apiFetch("/analytics/event", {
    method: "POST",
    body: JSON.stringify({ event }),
  }).catch(() => {
    // Best-effort: swallow network/API errors.
  });
}
