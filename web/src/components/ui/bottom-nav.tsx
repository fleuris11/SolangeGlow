"use client";

import { useTranslations } from "next-intl";

import { isActive, NAV_ITEMS } from "@/components/shell/nav-items";
import { cn } from "@/lib/cn";
import { Link, usePathname } from "@/lib/i18n/navigation";

/** Mobile bottom bar: five entries, each an icon and a word; "Publish" stands out. */
export function BottomNav() {
  const t = useTranslations("nav");
  const pathname = usePathname();

  return (
    <nav
      aria-label={t("label")}
      className="bg-carte border-trait pb-safe fixed inset-x-0 bottom-0 z-40 border-t lg:hidden"
    >
      <ul className="mx-auto grid max-w-[640px] grid-cols-5">
        {NAV_ITEMS.map(({ key, href, icon: Icon }) => {
          const active = isActive(pathname, href);
          const isCreate = key === "create";
          return (
            <li key={key}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "text-mention flex min-h-16 flex-col items-center justify-center gap-1 px-1 py-2 font-bold",
                  active ? "text-hibiscus" : "text-prune-doux",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "inline-flex items-center justify-center",
                    isCreate && "bg-hibiscus text-sur-hibiscus -mt-1 size-10 rounded-full",
                  )}
                >
                  <Icon
                    size={isCreate ? 26 : 28}
                    weight={active || isCreate ? "fill" : "duotone"}
                  />
                </span>
                <span className={cn(active && "text-prune")}>{t(key)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
