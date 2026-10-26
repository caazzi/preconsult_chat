import { afterEach, describe, expect, it, vi } from "vitest";

import { logEvent } from "./analytics";

describe("analytics gating", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("never fires without a session id (zero-PHI / Redis budget gate)", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    logEvent("intake_started", "");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("fires once with a session id", () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    logEvent("lifestyle_submitted", "sess-123");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/analytics/event");
  });
});
