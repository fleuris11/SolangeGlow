"use client";

import { CaretDown } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useId } from "react";

import { cn } from "@/lib/cn";

import { Flag } from "./flag";

export type PhoneCountry = { code: "BJ" | "FR"; prefix: string };

/** Benin and France first; "other" lets the person type any international number. */
export const PHONE_COUNTRIES: PhoneCountry[] = [
  { code: "BJ", prefix: "+229" },
  { code: "FR", prefix: "+33" },
];
export const OTHER_COUNTRY = "OTHER";

/** Builds the international number from the country and what was typed. */
export function toInternational(countryCode: string, typed: string): string {
  const digits = typed.replace(/[^\d+]/g, "");
  if (countryCode === OTHER_COUNTRY || digits.startsWith("+")) {
    return digits.startsWith("+") ? digits : `+${digits}`;
  }
  const country = PHONE_COUNTRIES.find((c) => c.code === countryCode);
  if (!country) return digits;
  // France: the leading 0 of national numbers is dropped (06… → +33 6…).
  // Benin: since 2024 numbers have 10 digits and keep their leading 01.
  const national = countryCode === "FR" ? digits.replace(/^0/, "") : digits;
  return `${country.prefix}${national}`;
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
  const current = PHONE_COUNTRIES.find((c) => c.code === country);

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="font-bold">
        {t("label")}
      </label>
      <div className="flex gap-2">
        <div className="rounded-field bg-poudre focus-within:border-hibiscus relative flex min-h-14 shrink-0 items-center gap-2 border-2 border-transparent pr-8 pl-3">
          <Flag country={current ? country : OTHER_COUNTRY} />
          <span aria-hidden className="font-bold">
            {current ? current.prefix : "+"}
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
            {PHONE_COUNTRIES.map((c) => (
              <option key={c.code} value={c.code}>
                {t(`countries.${c.code}`)} ({c.prefix})
              </option>
            ))}
            <option value={OTHER_COUNTRY}>{t("countries.other")}</option>
          </select>
        </div>
        <input
          id={inputId}
          type="tel"
          inputMode="tel"
          autoComplete={current ? "tel-national" : "tel"}
          autoFocus={autoFocus}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={current ? t(`placeholders.${current.code}`) : t("placeholders.other")}
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
