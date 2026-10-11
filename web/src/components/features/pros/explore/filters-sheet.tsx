"use client";

import { Clock, SealCheck, Van } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { PriceTag } from "@/components/ui/price-tag";
import { Sheet } from "@/components/ui/sheet";
import { SwitchRow } from "@/components/ui/switch-row";
import { getPlaces, type City } from "@/lib/api/pros";

import type { Filters, Sort } from "./filters";

// Price steps shown as choices, in the smallest unit of each currency.
const PRICE_STEPS: Record<string, number[]> = {
  XOF: [5000, 10000, 20000],
  EUR: [3000, 5000, 10000],
};
const CURRENCY_OF: Record<string, string> = { BJ: "XOF", FR: "EUR" };
const SORTS: Sort[] = ["relevance", "distance", "rating", "price"];

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filters: Filters;
  onApply: (changes: Partial<Filters>) => void;
};

/** Every filter on one sheet: place, hours, home visits, rating, price, order. */
export function FiltersSheet({ open, onOpenChange, filters, onApply }: Props) {
  const t = useTranslations("explore.filtersSheet");
  const [draft, setDraft] = useState<Filters>(filters);
  const places: City[] =
    useQuery({ queryKey: ["pros-places"], queryFn: getPlaces, staleTime: 600_000 }).data ?? [];
  const set = (changes: Partial<Filters>) => setDraft((current) => ({ ...current, ...changes }));
  const city = places.find((place) => place.city === draft.city);
  const currency = CURRENCY_OF[city?.country ?? ""] ?? draft.currency ?? "XOF";

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title={t("title")}>
      <div className="flex flex-col gap-6">
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 font-bold">{t("city")}</legend>
          <div className="flex flex-wrap gap-2">
            <Chip selected={!draft.city} onClick={() => set({ city: "", district: "" })}>
              {t("anyCity")}
            </Chip>
            {places.map((place) => (
              <Chip
                key={`${place.country}-${place.city}`}
                selected={draft.city === place.city}
                onClick={() =>
                  set({ city: place.city, district: "", lat: undefined, lng: undefined })
                }
              >
                {place.city}
              </Chip>
            ))}
          </div>
          {city && city.districts.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {city.districts.map((district) => (
                <Chip
                  key={district}
                  selected={draft.district === district}
                  onClick={() => set({ district: draft.district === district ? "" : district })}
                >
                  {district}
                </Chip>
              ))}
            </div>
          )}
        </fieldset>

        <div className="flex flex-col gap-3">
          <SwitchRow
            icon={<Clock size={28} weight="duotone" />}
            label={t("openNow")}
            description={t("openNowText")}
            checked={draft.openNow}
            onChange={(value) => set({ openNow: value })}
          />
          <SwitchRow
            icon={<Van size={28} weight="duotone" />}
            label={t("atHome")}
            description={t("atHomeText")}
            checked={draft.atHome}
            onChange={(value) => set({ atHome: value })}
          />
          <SwitchRow
            icon={<SealCheck size={28} weight="duotone" />}
            label={t("verified")}
            description={t("verifiedText")}
            checked={draft.verified}
            onChange={(value) => set({ verified: value })}
          />
        </div>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-bold">{t("rating")}</legend>
          <div className="flex flex-wrap gap-2">
            {[undefined, 4, 4.5].map((value) => (
              <Chip
                key={String(value)}
                selected={draft.ratingMin === value}
                onClick={() => set({ ratingMin: value })}
              >
                {value ? t("ratingMin", { rating: value }) : t("anyRating")}
              </Chip>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-bold">{t("price")}</legend>
          <div className="flex flex-wrap gap-2">
            <Chip selected={!draft.priceMax} onClick={() => set({ priceMax: undefined })}>
              {t("anyPrice")}
            </Chip>
            {(PRICE_STEPS[currency] ?? PRICE_STEPS.XOF!).map((value) => (
              <Chip
                key={value}
                selected={draft.priceMax === value && draft.currency === currency}
                onClick={() => set({ priceMax: value, currency })}
              >
                <PriceTag amountMinor={value} currency={currency} prefix={t("upTo")} />
              </Chip>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-bold">{t("sort")}</legend>
          <div className="flex flex-wrap gap-2">
            {SORTS.map((sort) => (
              <Chip
                key={sort}
                selected={(draft.sort ?? "relevance") === sort}
                onClick={() => set({ sort: sort === "relevance" ? undefined : sort })}
              >
                {t(`sorts.${sort}`)}
              </Chip>
            ))}
          </div>
        </fieldset>

        <Button size="lg" fullWidth onClick={() => onApply(draft)}>
          {t("apply")}
        </Button>
      </div>
    </Sheet>
  );
}
