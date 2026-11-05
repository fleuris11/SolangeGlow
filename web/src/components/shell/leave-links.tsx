"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { useMe } from "@/lib/auth/use-me";
import { Link } from "@/lib/i18n/navigation";

import { SignOutButton } from "./sign-out-button";

/** For someone signed in only: downloaded apart so that visitors do not pay for it (ADR-004). */
export function LeaveLinks({ icons }: { icons: { pro: ReactNode; signOut: ReactNode } }) {
  const t = useTranslations("proSpace");
  const { data: me } = useMe();
  if (!me) return null;
  return (
    <div className="border-trait flex flex-col gap-1 border-t pt-3">
      {me.roles.includes("pro") && (
        <Link
          href="/pro"
          className="hover:bg-poudre flex min-h-12 items-center gap-3 rounded-lg px-3 font-semibold"
        >
          {icons.pro}
          {t("proMode")}
        </Link>
      )}
      <SignOutButton icon={icons.signOut} />
    </div>
  );
}
