"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import type { Space } from "@/lib/navigation/space";

// The list of screens arrives only when it is opened (ADR-004).
const GoToDialog = dynamic(() => import("./go-to-dialog").then((m) => m.GoToDialog));

/**
 * « Go to… »: any screen in two keystrokes (Ctrl+K or Cmd+K), like the big apps, or with this
 * button. The list is the one of the space she is in: her professional space or her client side.
 */
export function GoTo({ space, className }: { space: Space; className?: string }) {
  const t = useTranslations("goTo");
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          className ??
          "press hover:bg-poudre text-prune-doux flex min-h-11 w-full items-center justify-between gap-2 rounded-lg px-3 text-left font-semibold"
        }
      >
        <span>{t("open")}</span>
        <kbd className="text-mention bg-poudre rounded px-1.5 py-0.5 font-sans">{t("keys")}</kbd>
      </button>
      {open && <GoToDialog space={space} open={open} onOpenChange={setOpen} />}
    </>
  );
}
