// 1:1 TypeScript port of src/preconsult/core/parsing.py.
//
// The Python source is the single source of truth. This port is validated in CI
// against the SAME vectors the Python implementation is tested with
// (contracts/parsing_vectors.json), so the two can never silently diverge.
// See docs/parsing-port-spec.md.

import emergencyTokens from "./generated/emergency_tokens.json";

/**
 * Split an accumulated stream buffer into individual questions.
 *
 * Handles numbered (1., 1)), dash-prefixed and plain newline-separated question
 * lists, mirroring the Python `split_questions`.
 */
export function splitQuestions(buffer: string): string[] {
  let qs = ("\n" + buffer)
    .split(/\n(?:\d+[.)]|-)\s*/)
    .map((q) => q.trim())
    .filter(Boolean);
  if (qs.length <= 1) {
    qs = buffer
      .trim()
      .split("\n")
      .map((q) => q.trim())
      .filter(Boolean);
  }
  return qs;
}

/**
 * True if the accumulated buffer signals an emergency red flag. Case-insensitive
 * substring match on the shared token list (imported from the generated
 * contract so there is one source of truth).
 */
export function isEmergencyTrigger(text: string): boolean {
  const lower = text.toLowerCase();
  return emergencyTokens.some((token: string) => lower.includes(token));
}

/**
 * Input-side counterpart to {@link isEmergencyTrigger}: whether any supplied
 * patient input signals a red flag. Reuses the same token list.
 */
export function hasEmergencyRedFlag(...texts: string[]): boolean {
  return isEmergencyTrigger(texts.filter(Boolean).join(" "));
}
