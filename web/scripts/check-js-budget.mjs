/**
 * JavaScript budget of public pages (ADR-004): run after `next build`.
 *
 * Pre-rendered pages: sums the gzip size of every script their HTML loads.
 * Pages rendered at each visit (a pro's showcase, Explore): same files, read from the
 * build manifests (framework, polyfills, layouts and page entries).
 * Fails above the budget.
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { runInNewContext } from "node:vm";
import { gzipSync } from "node:zlib";

const BUDGET_KB = 230;
const LOCALES = ["fr", "en", "sk"];
const STATIC_PAGES = ["/messages", "/me"];
const DYNAMIC_PAGES = {
  "/[locale]": "[locale]/(app)",
  "/[locale]/create": "[locale]/(app)/create",
  "/[locale]/p/<post>": "[locale]/(app)/p/[id]",
  "/[locale]/messages/<conversation>": "[locale]/(chat)/messages/[id]",
  "/[locale]/<pro>": "[locale]/(app)/[slug]",
  "/[locale]/explore": "[locale]/(app)/explore",
  "/[locale]/<pro>/shop": "[locale]/(app)/[slug]/shop",
  "/[locale]/<pro>/shop/<product>": "[locale]/(app)/[slug]/shop/[product]",
};
const NEXT_DIR = ".next";

function scriptsOf(html) {
  const found = new Set();
  for (const match of html.matchAll(/\/_next\/static\/[^"'\s)]+?\.js/g)) found.add(match[0]);
  return [...found].map((src) => src.replace("/_next/", ""));
}

function gzipKb(path) {
  return gzipSync(readFileSync(join(NEXT_DIR, path))).length / 1024;
}

function total(files) {
  return [...new Set(files)].reduce((sum, file) => sum + gzipKb(file), 0);
}

function manifestScripts(route) {
  const build = JSON.parse(readFileSync(join(NEXT_DIR, "build-manifest.json"), "utf8"));
  const file = join(NEXT_DIR, "server", "app", route, "page_client-reference-manifest.js");
  const sandbox = { globalThis: {} };
  sandbox.globalThis = sandbox;
  runInNewContext(readFileSync(file, "utf8"), sandbox);
  const manifest = Object.values(sandbox.__RSC_MANIFEST)[0];
  return [
    ...build.rootMainFiles,
    ...build.polyfillFiles,
    ...Object.values(manifest.entryJSFiles).flat(),
  ];
}

let failed = false;
const rows = [];
const report = (page, kb) => {
  const over = kb > BUDGET_KB;
  failed ||= over;
  rows.push({ page, "JS (KB gzip)": kb.toFixed(1), status: over ? "OVER" : "ok" });
};

for (const locale of LOCALES) {
  for (const page of STATIC_PAGES) {
    const file = join(NEXT_DIR, "server", "app", `${locale}${page}.html`);
    if (!existsSync(file)) {
      console.error(`Missing pre-rendered page: ${file} (is it still static?)`);
      failed = true;
      continue;
    }
    report(`/${locale}${page}`, total(scriptsOf(readFileSync(file, "utf8"))));
  }
}
for (const [page, route] of Object.entries(DYNAMIC_PAGES)) {
  report(page, total(manifestScripts(route)));
}

console.table(rows);
if (failed) {
  console.error(
    `JavaScript budget exceeded (${BUDGET_KB} KB gzip, see docs/adr/004-budget-javascript.md).`,
  );
  process.exit(1);
}
console.log(`All public pages are under ${BUDGET_KB} KB of JavaScript (gzip).`);
