"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { ApiError } from "@/lib/api/client";
import { getMyPro, myProQueryKey, type MyPro } from "@/lib/api/pros";

function processing(pro: MyPro | null | undefined): boolean {
  if (!pro) return false;
  const media = [
    pro.photo,
    pro.cover,
    pro.bio_voice,
    pro.place.itinerary_video,
    pro.place.landmarks_voice,
    ...pro.portfolio.map((item) => item.media),
  ];
  return media.some((item) => item?.status === "pending" || item?.status === "processing");
}

/** The pro's own showcase; null when she has none yet (« Become a pro »). */
export function useMyPro() {
  return useQuery({
    queryKey: myProQueryKey,
    queryFn: async () => {
      try {
        return await getMyPro();
      } catch (error) {
        if (error instanceof ApiError && error.code === "not_a_pro") return null;
        throw error;
      }
    },
    // Pictures and videos are processed in the background: look again until ready.
    refetchInterval: (query) => (processing(query.state.data) ? 2_500 : false),
  });
}

export function useSetMyPro() {
  const queryClient = useQueryClient();
  return useCallback((pro: MyPro) => queryClient.setQueryData(myProQueryKey, pro), [queryClient]);
}
