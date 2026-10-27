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
import { SESSION_FUNNEL_EVENTS, type FunnelEvent } from "../contracts/generated/funnel_events";

export type { FunnelEvent };

/**
 * Fire-and-forget funnel event. Session-gated keys are a no-op without a
 * `sessionId`; pre-session steps are allowed anonymously. Never throws —
 * analytics must not break the user flow.
 */
export function logEvent(event: FunnelEvent, sessionId = ""): void {
  // Only the Redis-backed tier needs a session; the pre-session steps are
  // counted in memory by the backend.
  if ((SESSION_FUNNEL_EVENTS as readonly string[]).includes(event) && !sessionId)
    return;
  void apiFetch("/analytics/event", {
    method: "POST",
    body: JSON.stringify({ event }),
  }).catch(() => {
    // Best-effort: swallow network/API errors.
  });
}
