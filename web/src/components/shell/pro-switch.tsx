"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { useMe } from "@/lib/auth/use-me";
import { Link } from "@/lib/i18n/navigation";

/** On a phone, a pro is one tap away from her space. */
export function ProSwitch({ icon }: { icon: ReactNode }) {
  const t = useTranslations("proSpace");
  const { data: me } = useMe();
  if (!me?.roles.includes("pro")) return null;
  return (
    <Link
      href="/pro"
      className="text-mention hover:bg-poudre inline-flex min-h-12 w-14 shrink-0 flex-col items-center justify-center rounded-lg text-center leading-none font-semibold"
    >
      {icon}
      <span>{t("badge")}</span>
    </Link>
  );
}
