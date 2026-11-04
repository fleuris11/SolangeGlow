"use client";

import { CaretDown } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useId } from "react";

import { useCountryNames } from "@/components/features/geo/country-select";
import { cn } from "@/lib/cn";
import { COUNTRIES } from "@/lib/geo/countries";

/** France by default: the launch starts there, and every country is one tap away. */
export const DEFAULT_PHONE_COUNTRY = "FR";

// These countries keep the leading 0 of their national numbers.
const KEEP_FIRST_ZERO = new Set(["BJ", "IT", "SM", "VA"]);

/** Builds the international number from the country and what was typed. */
export function toInternational(countryCode: string, typed: string): string {
  const digits = typed.replace(/[^\d+]/g, "");
  if (digits.startsWith("+")) return digits;
  const prefix = COUNTRIES.find(([code]) => code === countryCode)?.[1];
  if (!prefix) return `+${digits}`;
  return `${prefix}${KEEP_FIRST_ZERO.has(countryCode) ? digits : digits.replace(/^0/, "")}`;
}

type Props = {
  country: string;
  onCountryChange: (code: string) => void;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  autoFocus?: boolean;
};

/** Country (flag + prefix) and number, side by side, with big touch targets. */
export function PhoneField({ country, onCountryChange, value, onChange, error, autoFocus }: Props) {
  const t = useTranslations("auth.phone");
  const inputId = useId();
  const selectId = useId();
  const errorId = `${inputId}-error`;
  const countries = useCountryNames();
  const current = countries.find((c) => c.code === country);

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="font-bold">
        {t("label")}
      </label>
      <div className="flex gap-2">
        <div className="rounded-field bg-poudre focus-within:border-hibiscus relative flex min-h-14 shrink-0 items-center gap-2 border-2 border-transparent pr-8 pl-3">
          <span aria-hidden className="font-bold whitespace-nowrap">
            {current?.prefix ?? "+"}
          </span>
          <CaretDown aria-hidden size={16} weight="bold" className="absolute right-3" />
          <label htmlFor={selectId} className="sr-only">
            {t("country")}
          </label>
          <select
            id={selectId}
            value={country}
            onChange={(event) => onCountryChange(event.target.value)}
            className="absolute inset-0 cursor-pointer opacity-0"
          >
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name} ({c.prefix})
              </option>
            ))}
          </select>
        </div>
        <input
          id={inputId}
          type="tel"
          inputMode="tel"
          autoComplete="tel-national"
          autoFocus={autoFocus}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={t("placeholder")}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={cn(
            "rounded-field bg-poudre text-lead placeholder:text-prune-doux min-h-14 w-full min-w-0 border-2 px-4 font-bold tracking-wide outline-none",
            "focus:border-hibiscus",
            error ? "border-alerte" : "border-transparent",
          )}
        />
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-small text-alerte font-bold">
          {error}
        </p>
      )}
    </div>
  );
}
