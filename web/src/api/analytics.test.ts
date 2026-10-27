import { afterEach, describe, expect, it, vi } from "vitest";

import { logEvent } from "./analytics";

/** Read the event name out of a recorded fetch call. */
function postedEvent(call: unknown[]): string {
  const init = call[1] as RequestInit;
  return (JSON.parse(String(init.body)) as { event: string }).event;
}

describe("analytics storage tiers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fires a pre-session step without a session id", () => {
    // The session does not exist yet at this point in the flow: this event is
    // counted in memory by the backend, never in Redis.
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    logEvent("intake_started");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/analytics/event");
    expect((init as RequestInit).method).toBe("POST");
    expect(postedEvent(fetchSpy.mock.calls[0])).toBe("intake_started");
  });

  it("never fires a Redis funnel event without a session id", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    logEvent("lifestyle_submitted");
    logEvent("summary_generated", "");
    logEvent("pdf_downloaded", "");

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("fires a session event once with a session id", () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    logEvent("lifestyle_submitted", "sess-123");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/analytics/event");
  });
});
