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

// --- Social (feed, stories, a post, reviews) ---------------------------------------------

type Schemas = components["schemas"];

export async function feedOnServer(locale: string, city?: string): Promise<Schemas["PostPage"]> {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/feed", { params: { query: city ? { city } : {} } });
  return data ?? { results: [], next: null };
}

export async function storiesOnServer(locale: string, city?: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/stories", { params: { query: city ? { city } : {} } });
  return data ?? [];
}

/** A post, or null when it does not exist or is not visible to this visitor. */
export async function postOnServer(id: string, locale: string): Promise<Schemas["Post"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/posts/{post_id}", {
    params: { path: { post_id: id } },
  });
  if (response.status === 404 || response.status === 400) return null;
  if (!response.ok || !data) throw new Error(`Post ${id}: ${response.status}`);
  return data;
}

export async function reviewsOnServer(slug: string, locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/pros/{slug}/reviews", { params: { path: { slug } } });
  return data ?? null;
}

export async function personPostsOnServer(userId: string, locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/people/{user_id}/posts", {
    params: { path: { user_id: userId } },
  });
  return data ?? { results: [], next: null };
}

/** Public address of the site, for links shared on social networks (images, canonical). */
export const SITE_URL = (process.env.SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");

// --- Shops (module 4) ----------------------------------------------------------------------------

/** The shop of a pro, or null when she has none (or the shops are off in her country). */
export async function shopOnServer(
  slug: string,
  locale: string,
  category?: string,
): Promise<Schemas["ShopPage"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/pros/{slug}/shop", {
    params: { path: { slug }, query: category ? { category } : {} },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Shop ${slug}: ${response.status}`);
  return data;
}

export async function productOnServer(
  slug: string,
  productSlug: string,
  locale: string,
): Promise<Schemas["ProductDetail"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/pros/{slug}/shop/{product_slug}", {
    params: { path: { slug, product_slug: productSlug } },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Product ${productSlug}: ${response.status}`);
  return data;
}

export async function productReviewsOnServer(id: string, locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/shop/products/{product_id}/reviews", {
    params: { path: { product_id: id } },
  });
  return data ?? { average: null, count: 0, results: [] };
}

// --- France Selection (module 6) ------------------------------------------------------------------

export async function selectionOnServer(locale: string, aisle?: string) {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/selection/products", {
    params: { query: aisle ? { aisle: aisle as Schemas["AisleEnum"] } : {} },
  });
  if (!response.ok || !data) throw new Error(`Selection: ${response.status}`);
  return data;
}

export async function selectionProductOnServer(
  slug: string,
  locale: string,
): Promise<Schemas["SelectionProductDetail"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/selection/products/{slug}", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Selection ${slug}: ${response.status}`);
  return data;
}

export async function pickupPointsOnServer(locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/selection/pickup-points");
  return data ?? [];
}

// --- Appointments (module 8) ---------------------------------------------------------------------

/** The booking page of a pro, or null when she does not take online bookings. */
export async function bookingOnServer(
  slug: string,
  locale: string,
): Promise<Schemas["BookingPage"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/pros/{slug}/booking", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Booking ${slug}: ${response.status}`);
  return data;
}

// --- Glow Pro (module 8, Premium) ----------------------------------------------------------------

/** The booking widget of a salon (colour, allowed websites), or null when not offered. */
export async function widgetOnServer(slug: string, locale: string) {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/widget/{slug}", { params: { path: { slug } } });
  if (!response.ok || !data) return null;
  return data;
}

// --- Academy (module 7) --------------------------------------------------------------------------

export type CatalogueQuery = NonNullable<
  import("./schema").operations["academy_catalogue"]["parameters"]["query"]
>;

/** First page of the catalogue, rendered on the server. */
export async function catalogueOnServer(query: CatalogueQuery, locale: string) {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/academy/courses", { params: { query } });
  if (!response.ok || !data) throw new Error(`Catalogue: ${response.status}`);
  return data;
}

/** A course page, or null when it does not exist or is not published. */
export async function courseOnServer(
  slug: string,
  locale: string,
): Promise<Schemas["CourseDetail"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/academy/courses/{slug}", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Course ${slug}: ${response.status}`);
  return data;
}

/** The public check of a certificate, or null when the code is unknown. */
export async function certificateOnServer(
  code: string,
  locale: string,
): Promise<Schemas["CertificateCheck"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/academy/certificates/{code}", {
    params: { path: { code } },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Certificate: ${response.status}`);
  return data;
}

export async function livesOnServer(locale: string) {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/academy/lives");
  if (!response.ok || !data) throw new Error(`Lives: ${response.status}`);
  return data;
}

export async function tradesOnServer(locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/trades");
  return data ?? [];
}

/** Lives on air and coming soon in her country (home page band); empty when unreachable. */
export async function upcomingLivesOnServer(locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/live/upcoming");
  return data ?? [];
}

// --- Games (module 10) -----------------------------------------------------------------------

/** The home widget of the games (streak, points, quiz, wheel, challenge, winner). */
export async function glowTodayOnServer(locale: string): Promise<Schemas["GlowToday"] | null> {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/glow/today");
  return data ?? null;
}

/** Who invites, from her personal link (null when the code does not work). */
export async function inviteOnServer(code: string, locale: string) {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/glow/invite/{code}", { params: { path: { code } } });
  return data ?? null;
}

// --- Ads (module 12) ------------------------------------------------------------------------

/** The ads of a placement, counted as shown (null when ads cannot be reached). */
export async function adsOnServer(
  locale: string,
  query: { placement: Schemas["AdPlacementEnum"]; count?: number; city?: string; trade?: string },
): Promise<Schemas["AdList"] | null> {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/ads", { params: { query } });
  return data ?? null;
}

// --- Contents and help center (module 12) ---------------------------------------------------

/** The home banners written by the team (none when they cannot be reached). */
export async function homeBannersOnServer(locale: string): Promise<Schemas["Banner"][]> {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/content/banners");
  return data ?? [];
}

export async function pagesOnServer(locale: string): Promise<Schemas["PageSummary"][]> {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/content/pages");
  return data ?? [];
}

/** A published page (help, terms…), or null when it does not exist. */
export async function pageOnServer(slug: string, locale: string): Promise<Schemas["Page"] | null> {
  const api = await serverApi(locale);
  const { data, response } = await api.GET("/api/v1/content/pages/{slug}", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!response.ok || !data) throw new Error(`Page ${slug}: ${response.status}`);
  return data;
}

export async function faqOnServer(locale: string): Promise<Schemas["FaqTopic"][]> {
  const api = await serverApi(locale);
  const { data } = await api.GET("/api/v1/help/faq");
  return data ?? [];
}
