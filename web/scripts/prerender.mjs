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

const FAQ = [
  ["faq_q1", "faq_a1"],
  ["faq_q2", "faq_a2"],
  ["faq_q3", "faq_a3"],
  ["faq_q4", "faq_a4"],
  ["faq_q5", "faq_a5"],
];

// Self-contained so the prerendered page does not depend on which Tailwind
// classes happen to be in the bundle (it is built before this script runs).
const STYLE = `<style id="static-landing-style">
      #static-landing{min-height:100vh;box-sizing:border-box;max-width:48rem;margin:0 auto;padding:3rem 1.5rem;background:#0f172a;color:#e2e8f0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;text-align:center}
      #static-landing .badge{display:inline-block;margin:0 0 1.5rem;padding:.25rem .75rem;border-radius:9999px;background:rgba(34,197,94,.1);color:#4ade80;font-size:.75rem}
      #static-landing h1{margin:0 0 .5rem;font-size:1.75rem;line-height:1.2;color:#f8fafc}
      #static-landing .sub{margin:0;color:#94a3b8;font-size:.9375rem;line-height:1.6}
      #static-landing .meta{margin:.75rem 0 0;color:#94a3b8;font-size:.75rem}
      #static-landing .cta{display:inline-block;margin-top:1.5rem;padding:.875rem 1.5rem;border-radius:.5rem;background:#06b6d4;color:#020617;font-weight:600}
      #static-landing .how,#static-landing .faq{margin-top:3rem;text-align:left}
      #static-landing h2{margin:0 0 1rem;color:#cbd5e1;font-size:.8125rem;letter-spacing:.08em;text-transform:uppercase}
      #static-landing ol{list-style:none;margin:0;padding:0;display:grid;gap:1.25rem}
      #static-landing ol li{display:flex;gap:1rem}
      #static-landing .num{flex:none;display:flex;align-items:center;justify-content:center;width:2rem;height:2rem;border:1px solid rgba(34,211,238,.3);border-radius:9999px;background:rgba(34,211,238,.1);color:#a5f3fc;font-size:.75rem;font-weight:700}
      #static-landing ol strong{display:block;color:#f1f5f9}
      #static-landing ol li div span{display:block;margin-top:.25rem;color:#94a3b8;font-size:.875rem;line-height:1.5}
      #static-landing .faq h2{color:#f8fafc;font-size:1.25rem;letter-spacing:0;text-transform:none}
      #static-landing details{border:1px solid rgba(255,255,255,.1);border-radius:.75rem;margin-top:.5rem;padding:.75rem 1rem;background:rgba(15,23,42,.4)}
      #static-landing summary{cursor:pointer;color:#f1f5f9;font-size:.875rem;font-weight:700}
      #static-landing details p{margin:.5rem 0 0;color:#94a3b8;font-size:.875rem;line-height:1.6}
      #static-landing .closing{margin-top:2rem}
    </style>`;

const esc = (value) =>
  String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/** Read a required translation; a renamed key fails the build loudly. */
function copy(t, key) {
  const value = t[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`prerender: missing translation ${key}`);
  }
  return value;
}

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
  const steps = [
    ["01", copy(t, "step_how_1"), copy(t, "step_sub_1")],
    ["02", copy(t, "step_how_2"), copy(t, "step_sub_2")],
    ["03", copy(t, "step_how_3"), copy(t, "step_sub_3")],
  ]
    .map(
      ([number, title, sub]) =>
        `<li><span class="num" aria-hidden="true">${number}</span><div><strong>${esc(
          title,
        )}</strong><span>${esc(sub)}</span></div></li>`,
    )
    .join("\n          ");

  const faq = FAQ.map(
    ([question, answer], index) =>
      `<details${index === 0 ? " open" : ""}><summary>${esc(
        copy(t, question),
      )}</summary><p>${esc(copy(t, answer))}</p></details>`,
  ).join("\n        ");

  return `<main id="static-landing">
        <p class="badge">${esc(copy(t, "privacy_badge_landing"))}</p>
        <h1>${esc(copy(t, "hero_title"))}</h1>
        <p class="sub">${esc(copy(t, "hero_subtitle"))}</p>
        <p class="meta">${esc(copy(t, "landing_meta"))}</p>
        <p class="cta">${esc(copy(t, "start_cta"))}</p>

        <section class="how">
          <h2>${esc(copy(t, "how_title"))}</h2>
          <ol>
          ${steps}
          </ol>
        </section>

        <section class="faq">
          <h2>${esc(copy(t, "faq_title"))}</h2>
          ${faq}
        </section>

        <p class="cta closing">${esc(copy(t, "start_cta"))}</p>
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
    `<title>${esc(copy(t, "seo_title"))}</title>`,
    "<title>",
  );
  html = replaceBetween(
    html,
    /(<meta\s+name="description"\s+content=")([^"]*)("\s*\/?>)/,
    copy(t, "seo_description"),
    "meta description",
  );
  html = replaceBetween(
    html,
    /(<meta property="og:title" content=")([^"]*)("\s*\/?>)/,
    copy(t, "seo_title"),
    "og:title",
  );
  html = replaceBetween(
    html,
    /(<meta\s+property="og:description"\s+content=")([^"]*)("\s*\/?>)/,
    copy(t, "seo_description"),
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
