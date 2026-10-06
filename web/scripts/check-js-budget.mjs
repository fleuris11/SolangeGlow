/**
 * JavaScript budget of public pages (ADR-004): run after `next build`.
 * Sums the gzip size of every script a pre-rendered page loads at first visit,
 * and fails above the budget.
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const BUDGET_KB = 230;
const LOCALES = ["fr", "en", "sk"];
const PAGES = ["", "/messages", "/create", "/me"];
const NEXT_DIR = ".next";

function scriptsOf(html) {
  const found = new Set();
  for (const match of html.matchAll(/\/_next\/static\/[^"'\s)]+?\.js/g)) found.add(match[0]);
  return [...found];
}

function gzipKb(path) {
  return gzipSync(readFileSync(path)).length / 1024;
}

let failed = false;
const rows = [];
for (const locale of LOCALES) {
  for (const page of PAGES) {
    const file = join(NEXT_DIR, "server", "app", `${locale}${page}.html`);
    if (!existsSync(file)) {
      console.error(`Missing pre-rendered page: ${file} (is it still static?)`);
      failed = true;
      continue;
    }
    const total = scriptsOf(readFileSync(file, "utf8")).reduce(
      (sum, src) => sum + gzipKb(join(NEXT_DIR, src.replace("/_next/", ""))),
      0,
    );
    const over = total > BUDGET_KB;
    failed ||= over;
    rows.push({
      page: `/${locale}${page}`,
      "JS (KB gzip)": total.toFixed(1),
      status: over ? "OVER" : "ok",
    });
  }
}

console.table(rows);
if (failed) {
  console.error(
    `JavaScript budget exceeded (${BUDGET_KB} KB gzip, see docs/adr/004-budget-javascript.md).`,
  );
  process.exit(1);
}
console.log(`All public pages are under ${BUDGET_KB} KB of JavaScript (gzip).`);
