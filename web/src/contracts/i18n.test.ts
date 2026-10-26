import { describe, expect, it } from "vitest";

import { detectLang, getTranslations, isLang } from "./i18n";

describe("getTranslations", () => {
  it("returns the requested language dictionary", () => {
    expect(getTranslations("pt").start_cta).toBe(getTranslations("pt").start_cta);
    expect(getTranslations("en").title).toBe("PreConsult");
  });

  it("en and pt have identical key sets", () => {
    expect(Object.keys(getTranslations("en")).sort()).toEqual(
      Object.keys(getTranslations("pt")).sort(),
    );
  });
});

describe("isLang", () => {
  it("accepts supported codes only", () => {
    expect(isLang("en")).toBe(true);
    expect(isLang("pt")).toBe(true);
    expect(isLang("fr")).toBe(false);
    expect(isLang(undefined)).toBe(false);
  });
});

describe("detectLang", () => {
  it("prefers an explicit supported query param", () => {
    expect(detectLang("?lang=pt", "en-US,en;q=0.9")).toBe("pt");
  });

  it("ignores an unsupported query param and falls back to Accept-Language", () => {
    expect(detectLang("?lang=fr", "pt-BR,pt;q=0.9")).toBe("pt");
  });

  it("honors Accept-Language quality weights", () => {
    expect(detectLang("", "en-US;q=0.5,pt-BR;q=0.9")).toBe("pt");
  });

  it("defaults to English with no signal", () => {
    expect(detectLang("", undefined)).toBe("en");
    expect(detectLang("", "fr-FR,fr;q=0.9")).toBe("en");
  });
});
