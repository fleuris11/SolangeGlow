"use client";

import { Check } from "@phosphor-icons/react";
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
      <ul className="flex flex-wrap gap-2">
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
                  "inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold",
                  current
                    ? "border-prune bg-prune text-lait"
                    : "border-trait bg-poudre text-prune hover:border-prune-doux",
                )}
              >
                {current && <Check aria-hidden size={18} weight="bold" />}
                {t(code)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
