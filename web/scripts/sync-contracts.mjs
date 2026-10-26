#!/usr/bin/env node
// Copy the language-neutral contract artifacts produced by the Python source
// of truth (scripts/export_contracts.py) into the web app.
//
// The SPA must NOT hand-copy i18n strings or parsing behavior. It imports the
// generated JSON verbatim so a Python-side change can never silently drift.
// CI runs this and asserts the working tree is unchanged (mirrors the Python
// contracts-currency check), so a stale copy fails the build.
import { cpSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const contractsDir = resolve(repoRoot, "contracts");
const outDir = resolve(here, "..", "src", "contracts", "generated");

if (!existsSync(contractsDir)) {
  console.error(`contracts/ not found at ${contractsDir}. Run scripts/export_contracts.py first.`);
  process.exit(1);
}

mkdirSync(resolve(outDir, "i18n"), { recursive: true });
cpSync(resolve(contractsDir, "i18n", "en.json"), resolve(outDir, "i18n", "en.json"));
cpSync(resolve(contractsDir, "i18n", "pt.json"), resolve(outDir, "i18n", "pt.json"));
cpSync(resolve(contractsDir, "emergency_tokens.json"), resolve(outDir, "emergency_tokens.json"));
cpSync(resolve(contractsDir, "parsing_vectors.json"), resolve(outDir, "parsing_vectors.json"));

console.log(`Synced contracts into ${outDir}`);
