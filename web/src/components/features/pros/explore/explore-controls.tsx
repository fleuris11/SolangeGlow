"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { usePathname, useRouter } from "@/lib/i18n/navigation";

import { readFilters, toQuery, type Filters } from "./filters";

const FiltersSheet = dynamic(() => import("./filters-sheet").then((m) => m.FiltersSheet));

type Icons = { near: ReactNode; filters: ReactNode; map: ReactNode; list: ReactNode };

/**
 * Near me, filters, list or map: the only parts of Explore that need a script.
 * Icons are drawn by the server page (no icon code sent to the phone).
 */
export function ExploreControls({ icons }: { icons: Icons }) {
  const t = useTranslations("explore");
  const router = useRouter();
  const pathname = usePathname();
  const filters = readFilters(useSearchParams());
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState(false);

  const update = (changes: Partial<Filters>) =>
    router.replace({ pathname, query: toQuery({ ...filters, ...changes }) }, { scroll: false });

  const locate = () => {
    if (!navigator.geolocation) return setLocationError(true);
    setLocating(true);
    setLocationError(false);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        update({
          lat: Number(position.coords.latitude.toFixed(5)),
          lng: Number(position.coords.longitude.toFixed(5)),
          city: "",
          district: "",
          sort: "distance",
        });
      },
      () => {
        setLocating(false);
        setLocationError(true);
      },
      { enableHighAccuracy: false, timeout: 15_000, maximumAge: 300_000 },
    );
  };

  const active = [
    filters.city,
    filters.openNow,
    filters.atHome,
    filters.verified,
    filters.trained,
    filters.ratingMin,
    filters.priceMax,
  ].filter(Boolean).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <Button
          variant={filters.lat !== undefined ? "primary" : "secondary"}
          onClick={locate}
          disabled={locating}
        >
          {icons.near}
          {locating ? t("locating") : t("nearMe")}
        </Button>
        <Button variant="secondary" onClick={() => setFiltersOpen(true)}>
          {icons.filters}
          {active ? t("filtersCount", { count: active }) : t("filters")}
        </Button>
        <Button
          variant="quiet"
          onClick={() => update({ view: filters.view === "map" ? "list" : "map" })}
        >
          {filters.view === "map" ? icons.list : icons.map}
          {filters.view === "map" ? t("showList") : t("showMap")}
        </Button>
      </div>
      {locationError && (
        <p role="alert" className="text-alerte font-bold">
          {t("locationError")}
        </p>
      )}
      {filtersOpen && (
        <FiltersSheet
          open={filtersOpen}
          onOpenChange={setFiltersOpen}
          filters={filters}
          onApply={(changes) => {
            update(changes);
            setFiltersOpen(false);
          }}
        />
      )}
    </div>
  );
}
