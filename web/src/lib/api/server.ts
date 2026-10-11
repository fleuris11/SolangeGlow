/**
 * Calls made by the Next.js server (pages rendered on the server, e.g. a pro's showcase).
 * They go straight to Django (API_INTERNAL_URL) with the visitor's cookies and language,
 * so a pro sees her own draft and everyone gets texts in their language.
 */
import { cookies } from "next/headers";
import createClient from "openapi-fetch";

import { CLIENT_HEADER } from "./client";
import type { components, paths } from "./schema";

const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

async function serverApi(locale: string) {
  const cookieHeader = (await cookies()).toString();
  return createClient<paths>({
    baseUrl: API_INTERNAL_URL,
    headers: { ...CLIENT_HEADER, "Accept-Language": locale, cookie: cookieHeader },
    fetch: (request) => globalThis.fetch(request, { cache: "no-store" }),
  });
}

/** The showcase of a pro, or null when it does not exist or is not published. */
export async function getShowcaseOnServer(
  slug: string,
  locale: string,
): Promise<components["schemas"]["Showcase"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/pros/{slug}", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Showcase ${slug}: ${response.status}`);
  return data;
}

export type ServerSearchQuery = NonNullable<
  import("./schema").operations["pros_search"]["parameters"]["query"]
>;

/** First page of an Explore search, rendered on the server (visible before any script). */
export async function searchProsOnServer(query: ServerSearchQuery, locale: string) {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/pros", { params: { query } });
  if (!response.ok || !data) throw new Error(`Search: ${response.status}`);
  return data;
}

export async function placesOnServer(locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/pros/places");
  return data ?? [];
}

/** Public address of the site, for links shared on social networks (images, canonical). */
export const SITE_URL = (process.env.SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");
