"use client";

import { CaretRight, Storefront } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import type { Me } from "@/lib/api/accounts";
import { Link } from "@/lib/i18n/navigation";

/** « Ma vitrine » for a pro, « Devenir pro » for everyone else. */
export function ProEntry({ me }: { me: Me }) {
  const t = useTranslations("pros.entry");
  const isPro = me.roles.includes("pro");
  return (
    <Link
      href={isPro ? "/pro" : "/pro/start"}
      className="bg-poudre rounded-card flex items-center gap-4 p-4"
    >
      <Storefront aria-hidden size={32} weight="duotone" className="text-hibiscus shrink-0" />
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="font-bold">{isPro ? t("myShowcase") : t("becomePro")}</span>
        <span className="text-small text-prune-doux">
          {isPro ? t("myShowcaseText") : t("becomeProText")}
        </span>
      </span>
      <CaretRight aria-hidden size={20} weight="bold" />
    </Link>
  );
}
