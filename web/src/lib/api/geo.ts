import { api, unwrap } from "./client";

export const searchCities = (q: string, country?: string, signal?: AbortSignal) =>
  unwrap(
    api.GET("/api/v1/cities", {
      params: { query: { q, ...(country ? { country } : {}) } },
      signal,
    }),
  );
