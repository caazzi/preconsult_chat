// Drift guard: the generated contract copies in src/contracts/generated must be
// byte-for-byte identical to the Python-produced artifacts in contracts/.
// Mirrors the CI check; catching it in Vitest gives a fast local failure.

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const repoContracts = resolve(here, "..", "..", "..", "contracts");
const generated = resolve(here, "generated");

const FILES = [
  "i18n/en.json",
  "i18n/pt.json",
  "emergency_tokens.json",
  "parsing_vectors.json",
];

function read(path: string): string {
  return readFileSync(path, "utf-8");
}

describe("contract artifacts are in sync", () => {
  for (const rel of FILES) {
    it(rel, () => {
      expect(read(resolve(generated, rel))).toBe(read(resolve(repoContracts, rel)));
    });
  }
});
