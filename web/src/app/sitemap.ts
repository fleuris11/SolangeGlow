import type { MetadataRoute } from "next";

import { routing } from "@/lib/i18n/routing";
import { SITE_URL } from "@/lib/seo/alternates";
import { SITEMAP_KINDS, type SitemapKind } from "@/lib/seo/sitemaps";

const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const MAIN = [
  "",
  "/proposer-mes-services",
  "/comment-ca-marche",
  "/explore",
  "/selection",
  "/academie",
  "/aide",
  "/offrir",
  "/classements",
];

// Built on request and kept one hour: new pros and products come in without a deploy.
export const revalidate = 3600;

export async function generateSitemaps() {
  return SITEMAP_KINDS.map((id) => ({ id }));
}

async function entries(kind: Exclude<SitemapKind, "main">) {
  try {
    const response = await fetch(`${API_INTERNAL_URL}/api/v1/seo/sitemap/${kind}`, {
      headers: { "X-SG-Client": "web" },
      next: { revalidate },
    });
    if (!response.ok) return [];
    return (await response.json()) as { path: string; updated_at: string }[];
  } catch {
    return []; // the backend is not reachable (build): filled at the next refresh
  }
}

/** Each page in every language, with its translations (hreflang). */
function inEveryLanguage(path: string, lastModified?: string): MetadataRoute.Sitemap[number] {
  return {
    url: `${SITE_URL}/${routing.defaultLocale}${path}`,
    ...(lastModified ? { lastModified } : {}),
    alternates: {
      languages: Object.fromEntries(
        routing.locales.map((code) => [code, `${SITE_URL}/${code}${path}`]),
      ),
    },
  };
}

export default async function sitemap(props: {
  id: Promise<string>;
}): Promise<MetadataRoute.Sitemap> {
  const kind = (await props.id) as SitemapKind;
  if (kind === "main") return MAIN.map((path) => inEveryLanguage(path));
  const rows = await entries(kind);
  return rows.map((row) => inEveryLanguage(row.path, row.updated_at));
}
