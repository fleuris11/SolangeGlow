"use client";

import { CaretDown, MapPin } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState } from "react";

import { Chip } from "@/components/ui/chip";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";
import { usePreferences } from "@/lib/preferences/preferences-provider";

// The sheet (and its dialog library) is only downloaded when the picker is opened.
const Sheet = dynamic(() => import("@/components/ui/sheet").then((m) => m.Sheet), { ssr: false });
const CityField = dynamic(
  () => import("@/components/features/geo/city-field").then((m) => m.CityField),
  { ssr: false },
);

/** The chosen city, used to suggest nearby pros. Opens a sheet to change it. */
export function CityPicker({ className }: { className?: string }) {
  const t = useTranslations("city");
  const { city, update } = usePreferences();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const choose = (name: string) => {
    update({ city: name });
    setOpen(false);
    setTyped("");
    toast(name ? t("saved", { city: name }) : t("everywhere"));
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-label={city ? t("change", { city }) : t("choose")}
        className={cn(
          "hover:bg-poudre inline-flex min-h-12 min-w-0 items-center gap-1 rounded-full px-2 font-bold",
          className,
        )}
      >
        <MapPin aria-hidden size={22} className="shrink-0" />
        <span className="truncate">{city || t("choose")}</span>
        <CaretDown aria-hidden size={16} weight="bold" className="shrink-0" />
      </button>
      {open && (
        <Sheet open={open} onOpenChange={setOpen} title={t("title")} description={t("description")}>
          <div className="flex flex-col gap-4 pb-48">
            <CityField
              autoFocus
              showCountry
              label={t("search")}
              value={typed}
              onChange={setTyped}
              onPick={(picked) => choose(picked.name)}
            />
            <Chip selected={!city} onClick={() => choose("")}>
              {t("everywhereCta")}
            </Chip>
          </div>
        </Sheet>
      )}
    </>
  );
}
