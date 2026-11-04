/**
 * Demonstration photos and short videos (run by hand, inside the web container):
 *   docker compose exec web node scripts/fetch-media.mjs            download and prepare
 *   docker compose exec web node scripts/fetch-media.mjs --search   also propose candidates
 *
 * Reads scripts/media-sources.json (a curated list, with licences). Everything is downloaded
 * here: the site never links to another site's pictures. Writes:
 *   public/media/<slug>.webp         photos, at most 1600 px
 *   public/media/CREDITS.md          author, licence and source of everything
 *   src/lib/media/library.json       size, blurhash and dominant colour, used by the pages
 *   .media-cache/                    originals (not versioned); videos are encoded from here
 *                                    by scripts/encode-videos.sh
 *
 * With UNSPLASH_ACCESS_KEY and PEXELS_API_KEY (web/.env.local), --search lists new candidates
 * in .media-cache/candidates.json, licences checked by their own APIs. Without the keys it says
 * so and goes on: the curated list is enough to build the site.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { encode } from "blurhash";
import sharp from "sharp";

const SOURCES = JSON.parse(readFileSync("scripts/media-sources.json", "utf8"));
const CACHE = ".media-cache";
const PUBLIC = "public/media";
const LIBRARY = "src/lib/media/library.json";
const MAX_SIDE = 1600;
const QUALITY = 74;
const POLITE_DELAY_MS = 800;
const USER_AGENT = "SolangeGlowMediaFetch/1.0 (https://github.com/fleuris11/SolangeGlow)";
const QUERIES = [
  "black woman makeup",
  "braids hairstyle",
  "cornrows",
  "locs hairstyle",
  "wig install",
  "nail art dark skin",
  "african wax fabric sewing",
  "gele head wrap",
  "black hairdresser salon",
  "african wedding",
];

for (const dir of [CACHE, `${PUBLIC}/video`, "src/lib/media"]) mkdirSync(dir, { recursive: true });

function loadLocalEnv() {
  if (!existsSync(".env.local")) return;
  for (const line of readFileSync(".env.local", "utf8").split("\n")) {
    const match = line.match(/^(UNSPLASH_ACCESS_KEY|PEXELS_API_KEY)=(.+)$/);
    if (match) process.env[match[1]] = match[2].trim();
  }
}

async function download(item) {
  const extension = item.kind === "video" ? "video" : "image";
  const path = `${CACHE}/${item.slug}.${extension}`;
  if (existsSync(path)) return path;
  const answer = await fetch(item.url, { headers: { "User-Agent": USER_AGENT } });
  if (!answer.ok) throw new Error(`${item.slug}: HTTP ${answer.status}`);
  writeFileSync(path, Buffer.from(await answer.arrayBuffer()));
  await new Promise((resolve) => setTimeout(resolve, POLITE_DELAY_MS));
  return path;
}

async function preparePhoto(item, path) {
  const image = sharp(path, { limitInputPixels: false }).rotate();
  const resized = image.resize(MAX_SIDE, MAX_SIDE, { fit: "inside", withoutEnlargement: true });
  const output = `${PUBLIC}/${item.slug}.webp`;
  const info = await resized.clone().webp({ quality: QUALITY }).toFile(output);
  const { data, info: raw } = await resized
    .clone()
    .resize(32, 32, { fit: "inside" })
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  const { dominant } = await resized.clone().resize(64, 64, { fit: "inside" }).stats();
  const color = `#${[dominant.r, dominant.g, dominant.b]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("")}`;
  return {
    src: `/media/${item.slug}.webp`,
    width: info.width,
    height: info.height,
    blurhash: encode(new Uint8ClampedArray(data), raw.width, raw.height, 4, 4),
    color,
    bytes: info.size,
  };
}

async function search() {
  loadLocalEnv();
  const { UNSPLASH_ACCESS_KEY: unsplash, PEXELS_API_KEY: pexels } = process.env;
  if (!unsplash && !pexels) {
    console.log("--search: no Unsplash or Pexels key, nothing to search.");
    return;
  }
  const found = [];
  for (const query of QUERIES) {
    const q = encodeURIComponent(query);
    if (unsplash) {
      const url = `https://api.unsplash.com/search/photos?query=${q}&per_page=20`;
      const body = await (
        await fetch(url, { headers: { Authorization: `Client-ID ${unsplash}` } })
      ).json();
      for (const r of body.results ?? [])
        found.push({
          source: "Unsplash",
          query,
          url: r.urls.regular,
          page: r.links.html,
          author: r.user.name,
        });
    }
    if (pexels) {
      const url = `https://api.pexels.com/v1/search?query=${q}&per_page=20`;
      const body = await (await fetch(url, { headers: { Authorization: pexels } })).json();
      for (const r of body.photos ?? [])
        found.push({
          source: "Pexels",
          query,
          url: r.src.large2x,
          page: r.url,
          author: r.photographer,
        });
    }
  }
  writeFileSync(`${CACHE}/candidates.json`, JSON.stringify(found, null, 2));
  console.log(`${found.length} candidates in ${CACHE}/candidates.json`);
}

const library = {};
const failed = [];
for (const item of SOURCES) {
  try {
    const path = await download(item);
    const entry =
      item.kind === "image"
        ? await preparePhoto(item, path)
        : {
            src: `/media/video/${item.slug}.mp4`,
            poster: `/media/video/${item.slug}.webp`,
          };
    library[item.slug] = { kind: item.kind, category: item.category, ...entry };
    console.log("ok", item.slug, entry.bytes ? `${Math.round(entry.bytes / 1024)} KB` : "");
  } catch (error) {
    failed.push(item.slug);
    console.log("FAILED", item.slug, String(error).slice(0, 120));
  }
}
writeFileSync(LIBRARY, `${JSON.stringify(library, null, 2)}\n`);

const rows = SOURCES.filter((item) => library[item.slug]).map(
  (item) =>
    `| ${item.slug} | ${item.title.replaceAll("|", "-")} | ${(item.author || "not stated").replaceAll("|", "-")} | [${item.license.replaceAll("|", "-")}](${item.licenseUrl}) | [${item.source}](${item.page}) |`,
);
writeFileSync(
  `${PUBLIC}/CREDITS.md`,
  [
    "# Credits of the demonstration media",
    "",
    "Generated by scripts/fetch-media.mjs. The people shown are not pros registered on Solange Glow.",
    "",
    "| File | Title | Author | Licence | Source |",
    "| --- | --- | --- | --- | --- |",
    ...rows,
    "",
  ].join("\n"),
);

if (process.argv.includes("--search")) await search();
console.log(`${Object.keys(library).length} ready, ${failed.length} failed`, failed);
