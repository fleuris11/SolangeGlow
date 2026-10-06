"use client";

import { Bell } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";
import { Link, usePathname } from "@/lib/i18n/navigation";
import { useUnreadCount } from "@/lib/notifications/use-unread";

/** Bell + word, with the number of unread notifications (live). */
export function NotificationBell({ layout = "stacked" }: { layout?: "stacked" | "row" }) {
  const t = useTranslations("notifications");
  const unread = useUnreadCount();
  const pathname = usePathname();
  const active = pathname.startsWith("/notifications");
  const label = unread > 0 ? t("bellUnread", { count: unread }) : t("bell");

  return (
    <Link
      href="/notifications"
      aria-label={label}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative inline-flex shrink-0 items-center font-bold",
        layout === "stacked"
          ? "text-mention hover:bg-poudre min-h-12 min-w-14 flex-col justify-center rounded-2xl px-2"
          : "text-lead text-prune-doux hover:bg-poudre min-h-14 gap-3 rounded-full px-4",
        active && layout === "row" && "bg-poudre text-prune",
      )}
    >
      <span aria-hidden className="relative inline-flex">
        <Bell
          size={layout === "stacked" ? 24 : 28}
          weight={active ? "fill" : "duotone"}
          className={layout === "row" ? "text-hibiscus" : undefined}
        />
        {unread > 0 && (
          <span className="bg-hibiscus text-sur-hibiscus text-mention absolute -top-1.5 -right-2 inline-flex min-w-5 items-center justify-center rounded-full px-1 leading-5 font-bold">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </span>
      <span aria-hidden>{t("bell")}</span>
    </Link>
  );
}
