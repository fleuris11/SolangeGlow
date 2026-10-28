"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";

import { useMessagingUnread } from "@/lib/messaging/use-messaging-unread";

// The incoming call sheet, downloaded with the badge (signed-in people only).
const IncomingCall = dynamic(
  () => import("@/components/features/calls/incoming-call").then((m) => m.IncomingCall),
  { ssr: false },
);

/**
 * Number of conversations with unread messages, on the « Messages » entry of the menu.
 * Downloaded only for signed-in people (ADR-004); it also starts the messaging socket and
 * listens for incoming calls.
 */
export function MessagesBadge({ layout }: { layout: "icon" | "row" }) {
  const t = useTranslations("nav");
  const { count } = useMessagingUnread();
  return (
    <>
      {layout === "icon" && (
        // Drawn twice (bottom bar, computer menu): the bottom bar one listens for calls.
        // The badge sits inside the « Messages » link: clicks in the sheet stop here.
        <span hidden onClick={(event) => event.stopPropagation()}>
          <IncomingCall />
        </span>
      )}
      {count > 0 && (
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
      )}
    </>
  );
}
