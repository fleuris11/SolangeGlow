"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { cn } from "@/lib/cn";
import { Link, usePathname } from "@/lib/i18n/navigation";
import { useMe } from "@/lib/auth/use-me";

import { AudioToggle } from "./audio-toggle";
import { CityPicker } from "./city-picker";
import type { NavIcons } from "./nav-icons";
import { isActive, NAV_ITEMS } from "./nav-items";
import { NotificationBell } from "./notification-bell";

const MessagesBadge = dynamic(() => import("./messages-badge").then((m) => m.MessagesBadge));

/** Computer layout: navigation on the left, always visible. */
export function DesktopSidebar({ icons }: { icons: NavIcons }) {
  const t = useTranslations("nav");
  const tMeta = useTranslations("metadata");
  const pathname = usePathname();
  const { data: me } = useMe();

  return (
    <aside className="sticky top-0 hidden h-dvh flex-col gap-6 overflow-y-auto py-6 lg:flex">
      <Link href="/" className="rounded-card self-start">
        <Image src="/icons/logo.png" alt={tMeta("title")} width={160} height={78} priority />
      </Link>
      <nav aria-label={t("label")}>
        <ul className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ key, href }) => {
            const active = isActive(pathname, href);
            return (
              <li key={key}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "text-lead flex min-h-14 items-center gap-3 rounded-full px-4 font-bold",
                    active ? "bg-poudre text-prune" : "text-prune-doux hover:bg-poudre",
                    key === "create" && !active && "text-hibiscus",
                  )}
                >
                  <span
                    aria-hidden
                    className={cn("inline-flex", (active || key === "create") && "text-hibiscus")}
                  >
                    {active ? icons[key].on : icons[key].off}
                  </span>
                  {t(key)}
                  {me && key === "messages" && <MessagesBadge layout="row" />}
                </Link>
              </li>
            );
          })}
          <li>
            <NotificationBell layout="row" />
          </li>
        </ul>
      </nav>
      <div className="border-trait flex flex-col items-start gap-2 border-t pt-4">
        <CityPicker />
        <AudioToggle />
      </div>
      <LocaleSwitcher className="mt-auto" />
    </aside>
  );
}
