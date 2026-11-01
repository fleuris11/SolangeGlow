"use client";

import { useTranslations } from "next-intl";
import { useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { dismiss, dismissedRecently, visits, type InstallOffer } from "@/lib/pwa/install";

function subscribe(callback: () => void) {
  window.addEventListener("sg-installable", callback);
  return () => window.removeEventListener("sg-installable", callback);
}

const offer = () => window.__sgInstall ?? null;

/**
 * « Install Solange Glow on your phone »: only when the browser offers it, after a success
 * (`moment="success"`) or from the 3rd visit (`moment="visits"`), never twice in a month.
 */
export function InstallPrompt({ moment, icon }: { moment: "success" | "visits"; icon: ReactNode }) {
  const t = useTranslations("pwa");
  const available = useSyncExternalStore<InstallOffer | null>(subscribe, offer, () => null);
  const [hidden, setHidden] = useState(false);
  if (!available || hidden || dismissedRecently()) return null;
  if (moment === "visits" && visits() < 3) return null;

  async function install() {
    await available?.prompt();
    window.__sgInstall = undefined;
    setHidden(true);
  }

  return (
    <aside aria-label={t("title")} className="bg-poudre rounded-card flex flex-col gap-3 p-4">
      <p className="flex items-start gap-3 font-bold">
        {icon}
        {t("title")}
      </p>
      <p className="text-prune-doux">{t("text")}</p>
      <div className="flex flex-wrap gap-3">
        <Button onClick={install}>{t("install")}</Button>
        <Button
          variant="quiet"
          onClick={() => {
            dismiss();
            setHidden(true);
          }}
        >
          {t("later")}
        </Button>
      </div>
    </aside>
  );
}
