// SSE interview stream consumer.
//
// Wire contract (docs/api-contract.md §3): each event is one line
// `data: <json>` where <json> is EITHER a string text delta OR a terminal
// object `{"type":"questions","questions":[...]}`. Mid-stream errors are served
// as a normal SSE event (HTTP 200) holding a localized generic string, never an
// HTTP error. The structured list is authoritative when present.

import { apiUrl, ApiError, throwIfError } from "./client";
import { isEmergencyTrigger, splitQuestions } from "../contracts/parsing";

export type StreamCallbacks = {
  /** A text delta arrived (progressive rendering). */
  onText: (fullBuffer: string) => void;
  /** The model emitted an emergency red flag; abort immediately. */
  onEmergency: (buffer: string) => void;
  /** The stream finished; `questions` is the authoritative final list. */
  onDone: (questions: string[]) => void;
  onError?: (message: string) => void;
};

/**
 * Parse a single SSE `data:` payload into text or a structured question list.
 * Exported for unit testing.
 */
export type ParsedEvent =
  | { kind: "text"; value: string }
  | { kind: "questions"; value: string[] };

export function parseEventPayload(raw: string): ParsedEvent | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed === "string") return { kind: "text", value: parsed };
  if (
    parsed &&
    typeof parsed === "object" &&
    (parsed as { type?: unknown }).type === "questions" &&
    Array.isArray((parsed as { questions?: unknown }).questions)
  ) {
    const questions = (parsed as { questions: unknown[] }).questions.filter(
      (q): q is string => typeof q === "string",
    );
    return { kind: "questions", value: questions };
  }
  return null;
}

/**
 * Consume the interview-questions SSE stream for a session. Resolves when the
 * stream ends; never throws for mid-stream errors (calls onError instead).
 */
export async function streamInterviewQuestions(
  sessionId: string,
  cbs: StreamCallbacks,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(apiUrl("/interview-questions-stream"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    await throwIfError(resp);
  } catch (e) {
    const code = e instanceof ApiError ? e.code : "network_error";
    cbs.onError?.(code);
    return;
  }

  const reader = resp.body?.getReader();
  if (!reader) {
    cbs.onError?.("network_error");
    return;
  }

  const decoder = new TextDecoder();
  let pending = "";
  let textBuffer = "";
  let structured: string[] | null = null;
  let emergency = false;

  const handleLine = (line: string) => {
    if (!line.startsWith("data: ")) return;
    const event = parseEventPayload(line.slice("data: ".length));
    if (!event) return;
    if (event.kind === "questions") {
      structured = event.value;
      return;
    }
    textBuffer += event.value;
    if (isEmergencyTrigger(textBuffer)) {
      emergency = true;
      return;
    }
    cbs.onText(textBuffer);
  };

  while (!emergency) {
    const { done, value } = await reader.read();
    if (done) break;
    pending += decoder.decode(value, { stream: true });
    const lines = pending.split("\n");
    pending = lines.pop() ?? "";
    for (const line of lines) {
      handleLine(line);
      if (emergency) break;
    }
  }

  if (emergency) {
    cbs.onEmergency(textBuffer);
    return;
  }

  // Drain any trailing partial line.
  if (pending) handleLine(pending);

  const finalQuestions = structured ?? splitQuestions(textBuffer);
  cbs.onDone(finalQuestions);
}
