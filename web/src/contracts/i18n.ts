// i18n provider for the SPA. The translations are the generated, language-
// neutral artifacts (contracts/i18n/{en,pt}.json) copied verbatim from the
// Python source of truth by web/scripts/sync-contracts.mjs — never hand-edited.

import en from "./generated/i18n/en.json";
import pt from "./generated/i18n/pt.json";

export type Lang = "en" | "pt";

export type Translation = typeof en;

const dictionaries: Record<Lang, Translation> = { en, pt };

export const SUPPORTED_LANGS: Lang[] = ["en", "pt"];

export function isLang(value: unknown): value is Lang {
  return value === "en" || value === "pt";
}

export function getTranslations(lang: Lang): Translation {
  return dictionaries[lang] ?? dictionaries.en;
}

/**
 * Resolve the initial language the way the Reflex client does:
 *   1. explicit `?lang=` query parameter,
 *   2. otherwise the browser's `Accept-Language` (first supported match),
 *   3. otherwise English.
 * No cookie is read here — the SPA keeps locale in memory/URL only, consistent
 * with the zero-persistence posture.
 */
export function detectLang(
  search: string,
  acceptLanguage: string | null | undefined,
): Lang {
  const param = new URLSearchParams(search).get("lang")?.toLowerCase();
  if (isLang(param)) return param;

  const header = (acceptLanguage ?? "").split(",");
  const parsed: { code: Lang; q: number }[] = [];
  for (const entry of header) {
    const [rawCode, ...params] = entry.split(";");
    const code = rawCode.trim().toLowerCase().split("-")[0];
    if (!isLang(code)) continue;
    let q = 1.0;
    for (const param of params) {
      const m = /q=([\d.]+)/.exec(param);
      if (m) q = parseFloat(m[1]);
    }
    parsed.push({ code, q });
  }
  parsed.sort((a, b) => b.q - a.q);
  return parsed[0]?.code ?? "en";
}
