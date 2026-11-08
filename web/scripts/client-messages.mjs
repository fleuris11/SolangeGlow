/**
 * Which translations each page sends to the browser (performance: before this, every page sent
 * all of them, about 160 KB, inside its HTML).
 *
 * Follows the imports of every page and layout; below the first "use client" file, everything
 * is client code, and its useTranslations("namespace.part") calls name what the browser needs.
 * Writes src/lib/i18n/client-namespaces.json:
 *   "shell"      what the layouts, error and loading screens need (root provider)
 *   "<route>"    what one page needs, the route being the page file under src/app
 *
 *   node scripts/client-messages.mjs          write the file
 *   node scripts/client-messages.mjs --check  fail when the file is out of date (CI)
 */
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";

const SRC = resolve("src");
const APP = join(SRC, "app");
const OUT = join(SRC, "lib/i18n/client-namespaces.json");
const SHELL_FILES = new Set([
  "layout.tsx",
  "error.tsx",
  "not-found.tsx",
  "loading.tsx",
  "template.tsx",
  "global-error.tsx",
]);

const IMPORT =
  /(?:import|export)\s[^'"]*?from\s*["']([^"']+)["']|import\s*\(\s*["']([^"']+)["']\s*\)|import\s+["']([^"']+)["']/g;
const NAMESPACE = /useTranslations\(\s*["']([\w.-]+)["']/g;
const BOUND = /const\s+(\w+)\s*=\s*useTranslations\(\s*["']([\w.-]+)["']\s*\)/g;
const cache = new Map();

function walk(dir, found = []) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, found);
    else found.push(path);
  }
  return found;
}

function resolveImport(from, spec) {
  let base;
  if (spec.startsWith("@/")) base = join(SRC, spec.slice(2));
  else if (spec.startsWith(".")) base = resolve(dirname(from), spec);
  else return null;
  for (const candidate of [
    base,
    `${base}.tsx`,
    `${base}.ts`,
    join(base, "index.tsx"),
    join(base, "index.ts"),
  ]) {
    if (/\.(tsx?)$/.test(candidate) && existsSync(candidate) && statSync(candidate).isFile())
      return candidate;
  }
  return null;
}

/**
 * The message paths a file reads: "ns.key" when every use of `const t = useTranslations("ns")`
 * is t("key") (or t.rich / t.raw / t.markup / t.has with a written key); the whole "ns" as soon
 * as one key is computed or t is handed to someone else.
 */
function namespacesOf(text) {
  const paths = new Set();
  const bound = new Set();
  for (const [, name, ns] of text.matchAll(BOUND)) {
    bound.add(ns);
    const keys = new Set();
    let whole = false;
    const uses = new RegExp(`(?<![\\w.$'"\`])${name}(?![\\w$])(?!\\s*=\\s*useTranslations)`, "g");
    for (const use of text.matchAll(uses)) {
      const after = text.slice(use.index + name.length, use.index + name.length + 200);
      const literal = after.match(/^(?:\.(?:rich|raw|markup|has))?\(\s*["'`]([\w.-]+)["'`]\s*[,)]/);
      if (literal) keys.add(literal[1]);
      else whole = true;
    }
    if (whole || keys.size === 0) paths.add(ns);
    else keys.forEach((key) => paths.add(`${ns}.${key}`));
  }
  // useTranslations("ns") used another way (not bound to a constant): the whole namespace.
  for (const [, ns] of text.matchAll(NAMESPACE)) if (!bound.has(ns)) paths.add(ns);
  return [...paths];
}

function info(file) {
  if (!cache.has(file)) {
    const text = readFileSync(file, "utf8");
    const imports = [];
    for (const match of text.matchAll(IMPORT)) {
      const target = resolveImport(file, match[1] ?? match[2] ?? match[3]);
      if (target) imports.push(target);
    }
    cache.set(file, {
      client: /^\s*["']use client["']/.test(text),
      namespaces: namespacesOf(text),
      imports,
    });
  }
  return cache.get(file);
}

/** Namespaces used by client code reachable from these files. */
function needs(entries) {
  const found = new Set();
  const seen = new Set();
  const stack = entries.map((file) => [file, false]);
  while (stack.length) {
    const [file, underClient] = stack.pop();
    const key = `${file}|${underClient}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const node = info(file);
    const client = underClient || node.client;
    if (client) node.namespaces.forEach((ns) => found.add(ns));
    for (const target of node.imports) stack.push([target, client]);
  }
  // "a" already covers "a.b": keep the shortest paths only.
  const sorted = [...found].sort();
  return sorted.filter((ns) => !sorted.some((other) => ns.startsWith(`${other}.`)));
}

const files = walk(APP).filter((f) => /\.tsx?$/.test(f));
const result = { shell: needs(files.filter((f) => SHELL_FILES.has(f.split(/[\\/]/).pop()))) };
for (const page of files.filter((f) => /[\\/]page\.tsx$/.test(f)).sort()) {
  result[relative(APP, page).replaceAll("\\", "/")] = needs([page]);
}

const text = `${JSON.stringify(result, null, 2)}\n`;
if (process.argv.includes("--check")) {
  if (!existsSync(OUT) || readFileSync(OUT, "utf8") !== text) {
    console.error("src/lib/i18n/client-namespaces.json is out of date: run npm run messages:scope");
    process.exit(1);
  }
  console.log("Client translations per page: up to date");
} else {
  writeFileSync(OUT, text);
  console.log(`Wrote ${relative(process.cwd(), OUT)} (${Object.keys(result).length - 1} pages)`);
}
