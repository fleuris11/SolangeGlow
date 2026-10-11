"use client";

import { useQuery } from "@tanstack/react-query";

import { getMapConfig } from "@/lib/api/pros";

/** Map tiles and starting view, set in the admin (per country). */
export function useMapConfig(country?: string | null, enabled = true) {
  return useQuery({
    queryKey: ["map-config", country ?? ""],
    queryFn: () => getMapConfig(country ?? undefined),
    staleTime: 60 * 60_000,
    enabled,
  });
}
