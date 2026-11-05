"use client";

import { useLocale, useTranslations } from "next-intl";

import { cn } from "@/lib/cn";
import { Link, usePathname } from "@/lib/i18n/navigation";
import { routing } from "@/lib/i18n/routing";

/** Language choice, each written in its own language so anyone can find theirs. */
export function LocaleSwitcher({ className }: { className?: string }) {
  const t = useTranslations("locales");
  const locale = useLocale();
  const pathname = usePathname();

  return (
    <nav aria-label={t("label")} className={className}>
      <ul className="flex flex-wrap gap-1">
        {routing.locales.map((code) => {
          const current = code === locale;
          return (
            <li key={code}>
              <Link
                href={pathname}
                locale={code}
                hrefLang={code}
                lang={code}
                aria-current={current ? "true" : undefined}
                className={cn(
                  "text-small rounded-button inline-flex min-h-11 items-center px-2 font-semibold",
                  current ? "underline underline-offset-4" : "text-prune-doux hover:text-prune",
                )}
              >
                {t(code)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
