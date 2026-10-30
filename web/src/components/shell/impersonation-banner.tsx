"use client";

import { SignOut, UserSwitch } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { stopImpersonation } from "@/lib/api/help";

function nameOf(raw: string): string {
  try {
    return decodeURIComponent(raw.split("|")[1] ?? "");
  } catch {
    return "";
  }
}

/** Always on top while a team member uses the account of a member; everything is noted. */
export function ImpersonationBanner({ raw }: { raw: string }) {
  const t = useTranslations("impersonation");
  const [busy, setBusy] = useState(false);
  const name = nameOf(raw);

  async function stop() {
    setBusy(true);
    try {
      await stopImpersonation();
    } finally {
      // A full reload: nothing of the member stays in memory.
      window.location.replace(window.location.origin);
    }
  }

  return (
    <div
      role="alert"
      className="bg-hibiscus text-sur-hibiscus sticky top-0 z-50 flex flex-wrap items-center gap-3 px-4 py-2"
    >
      <UserSwitch size={24} weight="duotone" aria-hidden />
      <p className="min-w-0 flex-1 font-bold">
        {name ? t("asNamed", { name }) : t("asMember")}
        <span className="text-small block font-normal">{t("traced")}</span>
      </p>
      <button
        type="button"
        onClick={stop}
        disabled={busy}
        className="border-sur-hibiscus inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-5 font-bold disabled:opacity-50"
      >
        <SignOut size={20} aria-hidden />
        {t("stop")}
      </button>
    </div>
  );
}
