"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useToast } from "@/components/ui/toast";
import { getCountries } from "@/lib/api/accounts";
import { EVERYWHERE, readViewerCountry, writeViewerCountry } from "@/lib/geo/viewer-country";

/** « Show for »: the country whose feed, professionals, lives and courses she sees. */
export function CountryChoice() {
  const t = useTranslations("city.country");
  const toast = useToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const countries = useQuery({
    queryKey: ["countries"],
    queryFn: getCountries,
    staleTime: Infinity,
  });
  const [value, setValue] = useState(() => readViewerCountry() || EVERYWHERE);

  return (
    <label className="flex flex-col gap-1">
      <span className="font-semibold">{t("label")}</span>
      <select
        value={value}
        onChange={(event) => {
          const code = event.target.value;
          setValue(code);
          writeViewerCountry(code);
          const name = countries.data?.find((country) => country.code === code)?.name;
          toast(name ? t("saved", { country: name }) : t("everywhere"), "success");
          void queryClient.invalidateQueries();
          router.refresh();
        }}
        className="bg-poudre min-h-12 rounded-[14px] px-4"
      >
        <option value={EVERYWHERE}>{t("all")}</option>
        {(countries.data ?? [])
          .slice()
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((country) => (
            <option key={country.code} value={country.code}>
              {country.name}
            </option>
          ))}
      </select>
      <span className="text-small text-prune-doux">{t("hint")}</span>
    </label>
  );
}
