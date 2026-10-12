"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { getMessagingUnread, messagingUnreadKey } from "@/lib/api/messaging-unread";
import { useMe } from "@/lib/auth/use-me";

import { subscribe } from "./bus";

/** Conversations with unread messages (and message requests), kept live by the socket. */
export function useMessagingUnread(): { count: number; requests: number } {
  const { data: me } = useMe();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: messagingUnreadKey,
    queryFn: getMessagingUnread,
    enabled: !!me,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!me) return;
    // The socket code is downloaded only for signed-in people (ADR-004).
    void import("./socket").then(({ startSocket }) => startSocket());
    return subscribe((event) => {
      if (event.type === "hello" || event.type === "unread") {
        queryClient.setQueryData(messagingUnreadKey, {
          count: event.count,
          requests: event.requests,
        });
      }
    });
  }, [me, queryClient]);

  return me
    ? { count: data?.count ?? 0, requests: data?.requests ?? 0 }
    : { count: 0, requests: 0 };
}
