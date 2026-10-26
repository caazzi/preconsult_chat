// Validate the TypeScript parsing port against the shared contract vectors.
// Mirrors tests/test_contracts.py: the SAME vectors must pass on both the
// Python implementation and this port, so behavior cannot drift.

import { describe, expect, it } from "vitest";

import vectors from "./generated/parsing_vectors.json";
import { isEmergencyTrigger, splitQuestions } from "./parsing";

type SplitCase = { name: string; input: string; expected: string[] };
type EmergencyCase = { name: string; input: string; expected: boolean };

describe("splitQuestions (contract vectors)", () => {
  for (const c of vectors.split_questions as SplitCase[]) {
    it(c.name, () => {
      expect(splitQuestions(c.input)).toEqual(c.expected);
    });
  }
});

describe("isEmergencyTrigger (contract vectors)", () => {
  for (const c of vectors.is_emergency_trigger as EmergencyCase[]) {
    it(c.name, () => {
      expect(isEmergencyTrigger(c.input)).toBe(c.expected);
    });
  }
});
