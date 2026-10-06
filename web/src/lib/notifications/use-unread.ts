"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { getUnreadCount, notificationsQueryKey, unreadQueryKey } from "@/lib/api/notifications";
import { useMe } from "@/lib/auth/use-me";

/** Unread notifications of the signed-in person, kept live through a WebSocket. */
export function useUnreadCount(): number {
  const { data: me } = useMe();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: unreadQueryKey,
    queryFn: getUnreadCount,
    enabled: !!me,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!me) return;
    let stop: (() => void) | undefined;
    let cancelled = false;
    // The socket code is only downloaded for signed-in people (JS budget, ADR-004).
    void import("./realtime").then(({ connect }) => {
      if (cancelled) return;
      stop = connect((message) => {
        queryClient.setQueryData(unreadQueryKey, { unread: message.unread });
        if (message.notification) {
          void queryClient.invalidateQueries({ queryKey: notificationsQueryKey, exact: true });
        }
      });
    });
    return () => {
      cancelled = true;
      stop?.();
    };
  }, [me, queryClient]);

  return me ? (data?.unread ?? 0) : 0;
}
