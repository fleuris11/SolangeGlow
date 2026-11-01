"use client";

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { downloadMyData } from "@/lib/api/accounts";
import { useMe } from "@/lib/auth/use-me";

/** « Download my data »: every piece of data linked to her account, in a ZIP file. */
export function DataExportButton({ icon, className }: { icon: ReactNode; className: string }) {
  const t = useTranslations("me");
  const { data: me } = useMe();
  const [state, setState] = useState<"idle" | "busy" | "error">("idle");
  if (!me) return null;

  async function download() {
    setState("busy");
    try {
      const blob = await downloadMyData();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "solange-glow-my-data.zip";
      link.click();
      URL.revokeObjectURL(link.href);
      setState("idle");
    } catch {
      setState("error");
    }
  }

  return (
    <>
      <button type="button" onClick={download} disabled={state === "busy"} className={className}>
        {icon}
        {state === "busy" ? t("exportBusy") : t("export")}
      </button>
      {state === "error" && (
        <p role="alert" className="text-alerte font-bold">
          {t("exportError")}
        </p>
      )}
    </>
  );
}
