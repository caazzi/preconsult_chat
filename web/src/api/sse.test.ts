import { afterEach, describe, expect, it, vi } from "vitest";

import { parseEventPayload, streamInterviewQuestions } from "./sse";

describe("parseEventPayload", () => {
  it("parses a string text delta", () => {
    expect(parseEventPayload('"1. First?"')).toEqual({
      kind: "text",
      value: "1. First?",
    });
  });

  it("parses the structured terminal questions event", () => {
    expect(
      parseEventPayload('{"type":"questions","questions":["A?","B?"]}'),
    ).toEqual({ kind: "questions", value: ["A?", "B?"] });
  });

  it("drops non-string entries in the structured list", () => {
    expect(
      parseEventPayload('{"type":"questions","questions":["A?",5,null]}'),
    ).toEqual({ kind: "questions", value: ["A?"] });
  });

  it("returns null for malformed JSON", () => {
    expect(parseEventPayload("not json")).toBeNull();
  });

  it("returns null for an unrelated object", () => {
    expect(parseEventPayload('{"foo":"bar"}')).toBeNull();
  });

  it("parses a structured error event", () => {
    expect(
      parseEventPayload('{"type":"error","code":"llm_unavailable"}'),
    ).toEqual({ kind: "error", code: "llm_unavailable" });
  });

  it("defaults an error event without a usable code", () => {
    expect(parseEventPayload('{"type":"error"}')).toEqual({
      kind: "error",
      code: "internal_error",
    });
    expect(parseEventPayload('{"type":"error","code":42}')).toEqual({
      kind: "error",
      code: "internal_error",
    });
  });
});

function sseResponse(events: string[]): Response {
  const body = events.map((e) => `data: ${e}\n\n`).join("");
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function collect() {
  const state = {
    text: [] as string[],
    questions: null as string[] | null,
    emergency: false,
    error: false,
    errorCode: null as string | null,
  };
  return {
    state,
    cbs: {
      onText: (b: string) => state.text.push(b),
      onDone: (q: string[]) => (state.questions = q),
      onEmergency: () => (state.emergency = true),
      onError: (code: string) => {
        state.error = true;
        state.errorCode = code;
      },
    },
  };
}

describe("streamInterviewQuestions", () => {
  afterEach(() => vi.restoreAllMocks());

  it("prefers the structured terminal questions event", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      sseResponse([
        JSON.stringify("progressive text "),
        '{"type":"questions","questions":["Q1?","Q2?"]}',
      ]),
    );
    const { state, cbs } = collect();
    await streamInterviewQuestions("sess", cbs);
    expect(state.questions).toEqual(["Q1?", "Q2?"]);
  });

  it("falls back to splitQuestions over text deltas", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      sseResponse([JSON.stringify("1. Alpha?\n2. Beta?")]),
    );
    const { state, cbs } = collect();
    await streamInterviewQuestions("sess", cbs);
    expect(state.questions).toEqual(["Alpha?", "Beta?"]);
  });

  it("aborts on an emergency trigger in the accumulated text", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      sseResponse([
        JSON.stringify("[EMERGENCY ALERT] call 911 now"),
        '{"type":"questions","questions":["should not appear"]}',
      ]),
    );
    const { state, cbs } = collect();
    await streamInterviewQuestions("sess", cbs);
    expect(state.emergency).toBe(true);
    expect(state.questions).toBeNull();
  });

  it("surfaces a structured error event and its stable code", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      sseResponse([
        '{"type":"error","code":"llm_unavailable"}',
        JSON.stringify(" Service temporarily unavailable. Please try again."),
      ]),
    );
    const { state, cbs } = collect();
    await streamInterviewQuestions("sess", cbs);
    expect(state.error).toBe(true);
    expect(state.errorCode).toBe("llm_unavailable");
    // The localized text event is still delivered (back-compat with the plain
    // string consumer); the structured code is what adds the retry signal.
    expect(state.text[state.text.length - 1]).toContain(
      "Service temporarily unavailable",
    );
  });

  it("does not treat an unknown object event as an error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      sseResponse(['{"type":"future","foo":1}', JSON.stringify("1. Alpha?\n2. Beta?")]),
    );
    const { state, cbs } = collect();
    await streamInterviewQuestions("sess", cbs);
    expect(state.error).toBe(false);
    expect(state.questions).toEqual(["Alpha?", "Beta?"]);
  });
});
