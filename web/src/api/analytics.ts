// Funnel analytics. Event keys are pinned by docs/analytics-contract.md and
// must match the backend aggregation exactly.
//
// PRIVACY/BUDGET GATE: never emit an event without an active session id. Bots
// and early-exit visitors must not reach the analytics Redis write path (this
// preserves the free-tier Upstash quota and the zero-persistence posture).

import { apiFetch } from "./client";

export type FunnelEvent =
  | "intake_started"
  | "demographics_submitted"
  | "complaint_submitted"
  | "history_submitted"
  | "lifestyle_submitted"
  | "summary_generated"
  | "pdf_downloaded";

/**
 * Fire-and-forget funnel event. No-op when `sessionId` is empty. Never throws —
 * analytics must not break the user flow.
 */
export function logEvent(event: FunnelEvent, sessionId: string): void {
  if (!sessionId) return;
  void apiFetch("/analytics/event", {
    method: "POST",
    body: JSON.stringify({ event }),
  }).catch(() => {
    // Best-effort: swallow network/API errors.
  });
}
