"use client";

import { CaretDown, MapPin } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState } from "react";

import { Chip } from "@/components/ui/chip";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";
import { CITIES } from "@/lib/demo/data";
import { usePreferences } from "@/lib/preferences/preferences-provider";

// The sheet (and its dialog library) is only downloaded when the picker is opened.
const Sheet = dynamic(() => import("@/components/ui/sheet").then((m) => m.Sheet), { ssr: false });

/** The chosen city, used to suggest nearby pros. Opens a sheet to change it. */
export function CityPicker({ className }: { className?: string }) {
  const t = useTranslations("city");
  const { city, update } = usePreferences();
  const toast = useToast();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-label={t("change", { city })}
        className={cn(
          "hover:bg-poudre inline-flex min-h-12 min-w-0 items-center gap-1 rounded-full px-2 font-bold",
          className,
        )}
      >
        <MapPin aria-hidden size={22} weight="duotone" className="text-hibiscus shrink-0" />
        <span className="truncate">{city}</span>
        <CaretDown aria-hidden size={16} weight="bold" className="shrink-0" />
      </button>
      {open && (
        <Sheet open={open} onOpenChange={setOpen} title={t("title")} description={t("description")}>
          <ul className="flex flex-wrap gap-2">
            {CITIES.map((name) => (
              <li key={name}>
                <Chip
                  selected={name === city}
                  onClick={() => {
                    update({ city: name });
                    setOpen(false);
                    toast(t("saved", { city: name }));
                  }}
                >
                  {name}
                </Chip>
              </li>
            ))}
          </ul>
        </Sheet>
      )}
    </>
  );
}
