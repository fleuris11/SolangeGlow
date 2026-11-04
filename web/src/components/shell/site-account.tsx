"use client";

import { useTranslations } from "next-intl";

import { buttonClasses } from "@/components/ui/button";
import { useMe } from "@/lib/auth/use-me";
import { Link } from "@/lib/i18n/navigation";

/** Sign in, or back to her own account, from the site of a pro. */
export function SiteAccount() {
  const t = useTranslations("marketing");
  const { data: me } = useMe();
  return (
    <Link
      href={me ? "/me" : "/auth"}
      className={buttonClasses({
        variant: "secondary",
        className: "text-small min-h-11 px-2 leading-tight sm:px-3 sm:whitespace-nowrap",
      })}
    >
      {me ? t("myAccount") : t("signIn")}
    </Link>
  );
}
