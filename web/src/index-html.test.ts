import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

// The SPA shell is the canonical document now that it is served at /, so its
// static <head> is part of the contract (the Python host no longer supplies
// these tags). Assert against the source index.html that Vite ships.
const here = dirname(fileURLToPath(import.meta.url));
const indexHtml = readFileSync(resolve(here, "..", "index.html"), "utf8");
// Collapse the formatting whitespace so the assertions read like the tags.
const head = indexHtml.replace(/\s+/g, " ");

describe("index.html head", () => {
  it("is indexable", () => {
    expect(head).not.toContain("noindex");
    expect(head).not.toContain("nofollow");
  });

  it("has the document title and description", () => {
    expect(head).toContain(
      "<title>PreConsult: Privacy-First Medical Intake Assistant</title>",
    );
    expect(head).toContain(
      'name="description" content="Guided AI interview helper for patient intake with zero data persistence."',
    );
  });

  it("declares the canonical URL and the social preview tags", () => {
    expect(head).toContain(
      '<link rel="canonical" href="https://pre-consult.org/" />',
    );
    expect(head).toContain(
      'property="og:image" content="https://pre-consult.org/og-image.png"',
    );
    expect(head).toContain('property="og:image:width" content="1200"');
    expect(head).toContain('property="og:image:height" content="630"');
    expect(head).toContain(
      'property="og:title" content="PreConsult: Privacy-First Medical Intake Assistant"',
    );
    expect(head).toContain(
      'property="og:description" content="Guided AI interview helper for patient intake with zero data persistence."',
    );
  });
});
