"use client";

import { useLocale } from "next-intl";
import { useId, useMemo } from "react";

import { COUNTRIES } from "@/lib/geo/countries";

/** The names of the countries, in the language of the person, in her alphabet order. */
export function useCountryNames() {
  const locale = useLocale();
  return useMemo(() => {
    const names = new Intl.DisplayNames([locale], { type: "region" });
    return [...COUNTRIES]
      .map(([code, prefix]) => ({ code, prefix, name: names.of(code) ?? code }))
      .sort((a, b) => a.name.localeCompare(b.name, locale));
  }, [locale]);
}

export function CountrySelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (code: string) => void;
}) {
  const countries = useCountryNames();
  const id = useId();
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="font-bold">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="border-trait bg-carte rounded-field min-h-12 w-full border-2 px-3 font-normal"
      >
        {countries.map((country) => (
          <option key={country.code} value={country.code}>
            {country.name}
          </option>
        ))}
      </select>
    </div>
  );
}
