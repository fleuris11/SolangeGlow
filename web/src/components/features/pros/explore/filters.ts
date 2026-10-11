/** Explore filters live in the address (shareable, back button friendly). */
import type { SearchQuery } from "@/lib/api/pros";

export type Sort = "relevance" | "distance" | "rating" | "price";

export type Filters = {
  q: string;
  trade: string;
  city: string;
  district: string;
  lat?: number;
  lng?: number;
  radius?: number;
  openNow: boolean;
  atHome: boolean;
  verified: boolean;
  ratingMin?: number;
  priceMax?: number;
  currency: string;
  sort?: Sort;
  view: "list" | "map";
};

const SORTS: Sort[] = ["relevance", "distance", "rating", "price"];

function number(value: string | null): number | undefined {
  if (value === null || value === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function readFilters(params: URLSearchParams): Filters {
  const sort = params.get("sort") as Sort | null;
  return {
    q: params.get("q") ?? "",
    trade: params.get("trade") ?? "",
    city: params.get("city") ?? "",
    district: params.get("district") ?? "",
    lat: number(params.get("lat")),
    lng: number(params.get("lng")),
    radius: number(params.get("radius")),
    openNow: params.get("open") === "1",
    atHome: params.get("home") === "1",
    verified: params.get("verified") === "1",
    ratingMin: number(params.get("rating")),
    priceMax: number(params.get("price")),
    currency: params.get("currency") ?? "XOF",
    sort: sort && SORTS.includes(sort) ? sort : undefined,
    view: params.get("view") === "map" ? "map" : "list",
  };
}

export function toQuery(filters: Filters): Record<string, string> {
  const query: Record<string, string> = {};
  const set = (key: string, value: string | number | undefined | false) => {
    if (value !== undefined && value !== "" && value !== false) query[key] = String(value);
  };
  set("q", filters.q);
  set("trade", filters.trade);
  set("city", filters.city);
  set("district", filters.district);
  set("lat", filters.lat);
  set("lng", filters.lng);
  set("radius", filters.radius);
  set("open", filters.openNow && "1");
  set("home", filters.atHome && "1");
  set("verified", filters.verified && "1");
  set("rating", filters.ratingMin);
  set("price", filters.priceMax);
  if (filters.priceMax) set("currency", filters.currency);
  set("sort", filters.sort);
  set("view", filters.view === "map" && "map");
  return query;
}

/** The API query of the filters (without the cursor). */
export function toApiQuery(filters: Filters): SearchQuery {
  return {
    ...(filters.q ? { q: filters.q } : {}),
    ...(filters.trade ? { trade: filters.trade } : {}),
    ...(filters.city ? { city: filters.city } : {}),
    ...(filters.district ? { district: filters.district } : {}),
    ...(filters.lat !== undefined && filters.lng !== undefined
      ? { lat: filters.lat, lng: filters.lng, radius_km: filters.radius ?? 10 }
      : {}),
    ...(filters.openNow ? { open_now: true } : {}),
    ...(filters.atHome ? { at_home: true } : {}),
    ...(filters.verified ? { verified: true } : {}),
    ...(filters.ratingMin ? { rating_min: filters.ratingMin } : {}),
    ...(filters.priceMax ? { price_max: filters.priceMax, currency: filters.currency } : {}),
    ...(filters.sort ? { sort: filters.sort } : {}),
  };
}

/** Accepts what Next gives a page as searchParams. */
export function paramsOf(record: Record<string, string | string[] | undefined>): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(record)) {
    if (typeof value === "string") params.set(key, value);
    else if (Array.isArray(value) && value[0] !== undefined) params.set(key, value[0]);
  }
  return params;
}
