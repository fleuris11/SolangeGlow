"use client";

import { useQuery } from "@tanstack/react-query";

import { getPlatform, platformQueryKey } from "@/lib/api/platform";

/**
 * Whether online payment is open. Free launch: the owner keeps it closed in the admin, and the
 * screens say that it opens soon instead of starting a payment. Unknown (loading, offline): open,
 * the server refuses anyway.
 */
export function usePaymentsOpen(): boolean {
  const query = useQuery({
    queryKey: platformQueryKey,
    queryFn: getPlatform,
    staleTime: 5 * 60 * 1000,
  });
  return query.data?.payments_open ?? true;
}
