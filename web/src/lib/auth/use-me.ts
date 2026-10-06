"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { getMe, meQueryKey, type Me } from "@/lib/api/accounts";

/** The signed-in person (null for a visitor). Shared by every screen through React Query. */
export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: getMe,
    staleTime: 60_000,
    retry: false,
    // A new photo is processed in the background: check again until it is ready.
    refetchInterval: (query) => {
      const status = query.state.data?.photo?.status;
      return status === "pending" || status === "processing" ? 2_000 : false;
    },
  });
}

/** Replace the cached person after a change made on the server. */
export function useSetMe() {
  const queryClient = useQueryClient();
  return useCallback((me: Me | null) => queryClient.setQueryData(meQueryKey, me), [queryClient]);
}
