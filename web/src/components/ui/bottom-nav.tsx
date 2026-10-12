"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import type { NavIcons } from "@/components/shell/nav-icons";
import { isActive, NAV_ITEMS } from "@/components/shell/nav-items";
import { cn } from "@/lib/cn";
import { Link, usePathname } from "@/lib/i18n/navigation";
import { useMe } from "@/lib/auth/use-me";

// Signed-in people only: the badge and the messaging socket (ADR-004).
const MessagesBadge = dynamic(() =>
  import("@/components/shell/messages-badge").then((m) => m.MessagesBadge),
);

/** Mobile bottom bar: five entries, each an icon and a word; "Publish" stands out. */
export function BottomNav({ icons }: { icons: NavIcons }) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const { data: me } = useMe();

  return (
    <nav
      aria-label={t("label")}
      className="bg-carte border-trait pb-safe fixed inset-x-0 bottom-0 z-40 border-t lg:hidden"
    >
      <ul className="mx-auto grid max-w-[640px] grid-cols-5">
        {NAV_ITEMS.map(({ key, href }) => {
          const active = isActive(pathname, href);
          const isCreate = key === "create";
          return (
            <li key={key}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "text-mention relative flex min-h-16 flex-col items-center justify-center gap-1 px-1 py-2 font-bold",
                  active ? "text-hibiscus" : "text-prune-doux",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "relative inline-flex items-center justify-center",
                    isCreate && "bg-hibiscus text-sur-hibiscus -mt-1 size-10 rounded-full",
                  )}
                >
                  {active || isCreate ? icons[key].on : icons[key].off}
                </span>
                <span className={cn(active && "text-prune")}>{t(key)}</span>
                {me && key === "messages" && <MessagesBadge layout="icon" />}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
