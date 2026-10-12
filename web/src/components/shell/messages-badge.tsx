"use client";

import { useTranslations } from "next-intl";

import { useMessagingUnread } from "@/lib/messaging/use-messaging-unread";

/**
 * Number of conversations with unread messages, on the « Messages » entry of the menu.
 * Downloaded only for signed-in people (ADR-004); it also starts the messaging socket.
 */
export function MessagesBadge({ layout }: { layout: "icon" | "row" }) {
  const t = useTranslations("nav");
  const { count } = useMessagingUnread();
  if (count <= 0) return null;
  return (
    <span
      className={
        layout === "icon"
          ? "bg-hibiscus text-sur-hibiscus text-mention absolute top-1 left-1/2 ml-2 inline-flex min-w-5 items-center justify-center rounded-full px-1 leading-5 font-bold"
          : "bg-hibiscus text-sur-hibiscus text-mention ml-auto inline-flex min-w-6 items-center justify-center rounded-full px-1.5 leading-6"
      }
    >
      <span aria-hidden>{count > 99 ? "99+" : count}</span>
      <span className="sr-only">{t("unreadMessages", { count })}</span>
    </span>
  );
}
