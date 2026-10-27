#!/usr/bin/env node
/**
 * Prerender the landing page into the built document.
 *
 * The SPA renders the landing at runtime, so the shipped `index.html` has an
 * empty `#root` and a crawler (or a visitor with JavaScript off / on a slow
 * connection) sees a blank page — even though `sitemap.xml` and `llms.txt`
 * point at it. This writes the same copy into `#root` before the bundle loads,
 * in each supported language:
 *
 *   dist/index.html      English   (served at /)
 *   dist/index.pt.html   Portuguese (served at /?lang=pt by SPAStaticFiles)
 *
 * The app removes the block (and its style) before it mounts, so React still
 * owns `#root` and there is no hydration mismatch to get wrong.
 *
 * Copy comes from the generated contracts — the same JSON the SPA reads — so
 * `core/i18n.py` stays the single source of truth. Every marker in the built
 * document is required: a missing one fails the build instead of silently
 * shipping a half-prerendered page.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const DIST = resolve("dist");
const I18N = resolve("src/contracts/generated/i18n");
const ORIGIN = "https://pre-consult.org";

/** English is the default document; Portuguese gets its own crawler URL. */
const LANGS = [
  { code: "en", file: "index.html", path: "/" },
  { code: "pt", file: "index.pt.html", path: "/?lang=pt" },
];

// Self-contained so the prerendered page does not depend on which Tailwind
// classes happen to be in the bundle (it is built before this script runs).
const STYLE = `<style id="static-landing-style">
      #static-landing{min-height:100vh;box-sizing:border-box;max-width:48rem;margin:0 auto;padding:3rem 1.5rem;background:#0f172a;color:#e2e8f0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;text-align:center}
      #static-landing .badge{display:inline-block;margin:0 0 1.5rem;padding:.25rem .75rem;border-radius:9999px;background:rgba(34,197,94,.1);color:#4ade80;font-size:.75rem}
      #static-landing h1{margin:0 0 .5rem;font-size:1.5rem;line-height:1.25;color:#f8fafc}
      #static-landing .sub{margin:0;color:#94a3b8;font-size:.875rem}
      #static-landing ul{list-style:none;margin:2rem 0;padding:0;display:grid;gap:.75rem}
      #static-landing li{border:1px solid rgba(255,255,255,.1);border-radius:.75rem;padding:1rem}
      #static-landing li strong{display:block;color:#f1f5f9}
      #static-landing li span{display:block;margin-top:.25rem;color:#94a3b8;font-size:.8125rem}
      #static-landing .cta{display:inline-block;margin-top:1rem;padding:.875rem 1.25rem;border-radius:.5rem;background:#06b6d4;color:#020617;font-weight:600}
    </style>`;

const esc = (value) =>
  String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/** Replace a whole match; throws when the built document lacks it. */
function replaceOnce(html, pattern, value, label) {
  let hit = false;
  const out = html.replace(pattern, () => {
    hit = true;
    return value;
  });
  if (!hit) throw new Error(`prerender: no ${label} in the built document`);
  return out;
}

/** Replace a value between two captured parts (attribute prefix/suffix). */
function replaceBetween(html, pattern, value, label) {
  let hit = false;
  const out = html.replace(pattern, (_match, before, _current, after) => {
    hit = true;
    return `${before}${esc(value)}${after}`;
  });
  if (!hit) throw new Error(`prerender: no ${label} in the built document`);
  return out;
}

/** Insert a snippet immediately after a match; throws when it is missing. */
function insertAfter(html, pattern, snippet, label) {
  let hit = false;
  const out = html.replace(pattern, (match) => {
    hit = true;
    return `${match}\n    ${snippet}`;
  });
  if (!hit) throw new Error(`prerender: no ${label} in the built document`);
  return out;
}

function landing(t) {
  return `<main id="static-landing">
        <p class="badge">${esc(t.privacy_badge_landing)}</p>
        <h1>${esc(t.hero_title)}</h1>
        <p class="sub">${esc(t.hero_subtitle)}</p>
        <ul>
          <li><strong>${esc(t.step_how_1)}</strong><span>${esc(t.step_sub_1)}</span></li>
          <li><strong>${esc(t.step_how_2)}</strong><span>${esc(t.step_sub_2)}</span></li>
          <li><strong>${esc(t.step_how_3)}</strong><span>${esc(t.step_sub_3)}</span></li>
        </ul>
        <p class="cta">${esc(t.start_cta)}</p>
      </main>`;
}

const alternates = LANGS.map(
  (lang) =>
    `<link rel="alternate" hreflang="${lang.code}" href="${ORIGIN}${lang.path}" />`,
)
  .concat(`<link rel="alternate" hreflang="x-default" href="${ORIGIN}/" />`)
  .join("\n    ");

const base = readFileSync(resolve(DIST, "index.html"), "utf8");

for (const { code, file, path } of LANGS) {
  const t = JSON.parse(readFileSync(resolve(I18N, `${code}.json`), "utf8"));

  let html = base;
  html = replaceOnce(html, /<html lang="[^"]*">/, `<html lang="${code}">`, "<html lang>");
  html = replaceOnce(
    html,
    /<title>[^<]*<\/title>/,
    `<title>${esc(t.seo_title)}</title>`,
    "<title>",
  );
  html = replaceBetween(
    html,
    /(<meta\s+name="description"\s+content=")([^"]*)("\s*\/?>)/,
    t.seo_description,
    "meta description",
  );
  html = replaceBetween(
    html,
    /(<meta property="og:title" content=")([^"]*)("\s*\/?>)/,
    t.seo_title,
    "og:title",
  );
  html = replaceBetween(
    html,
    /(<meta\s+property="og:description"\s+content=")([^"]*)("\s*\/?>)/,
    t.seo_description,
    "og:description",
  );
  html = replaceBetween(
    html,
    /(<link rel="canonical" href=")([^"]*)("\s*\/?>)/,
    `${ORIGIN}${path}`,
    "canonical",
  );
  html = insertAfter(
    html,
    /<link rel="canonical" href="[^"]*" \/>/,
    alternates,
    "canonical",
  );
  html = replaceOnce(
    html,
    /<div id="root"><\/div>/,
    `<div id="root">\n      ${landing(t)}\n    </div>`,
    "#root",
  );
  html = replaceOnce(html, /<\/head>/, `${STYLE}\n  </head>`, "</head>");

  writeFileSync(resolve(DIST, file), html);
  console.log(`prerender: ${file} (${code}, ${html.length} bytes)`);
}
