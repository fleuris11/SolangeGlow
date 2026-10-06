"use client";

import { useLocale, useTranslations } from "next-intl";
import { useId, useMemo } from "react";

export type BirthDate = { day: string; month: string; year: string };

export const EMPTY_BIRTH_DATE: BirthDate = { day: "", month: "", year: "" };

/** "1995-04-12", or null while incomplete or impossible (31 February). */
export function toIsoDate({ day, month, year }: BirthDate): string | null {
  if (!day || !month || !year) return null;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  if (date.getUTCDate() !== Number(day)) return null;
  return date.toISOString().slice(0, 10);
}

const selectClass =
  "rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-3 text-lead font-bold outline-none";

/** Day, month (written out) and year: easier than a calendar on a small phone. */
export function BirthDateField({
  value,
  onChange,
}: {
  value: BirthDate;
  onChange: (value: BirthDate) => void;
}) {
  const t = useTranslations("welcome.birth");
  const locale = useLocale();
  const id = useId();
  const months = useMemo(() => {
    const format = new Intl.DateTimeFormat(locale, { month: "long", timeZone: "UTC" });
    return Array.from({ length: 12 }, (_, i) => format.format(new Date(Date.UTC(2000, i, 1))));
  }, [locale]);
  const thisYear = new Date().getFullYear();
  const years = Array.from({ length: 100 }, (_, i) => String(thisYear - 10 - i));

  return (
    <fieldset className="flex min-w-0 flex-col gap-3">
      <legend className="mb-3 font-bold">{t("label")}</legend>
      <div className="grid grid-cols-[1fr_1.6fr_1.3fr] gap-2">
        <div className="flex flex-col gap-1">
          <label htmlFor={`${id}-day`} className="text-small text-prune-doux">
            {t("day")}
          </label>
          <select
            id={`${id}-day`}
            value={value.day}
            onChange={(event) => onChange({ ...value, day: event.target.value })}
            className={selectClass}
          >
            <option value="">–</option>
            {Array.from({ length: 31 }, (_, i) => String(i + 1)).map((day) => (
              <option key={day} value={day}>
                {day}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor={`${id}-month`} className="text-small text-prune-doux">
            {t("month")}
          </label>
          <select
            id={`${id}-month`}
            value={value.month}
            onChange={(event) => onChange({ ...value, month: event.target.value })}
            className={selectClass}
          >
            <option value="">–</option>
            {months.map((name, i) => (
              <option key={name} value={String(i + 1)}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor={`${id}-year`} className="text-small text-prune-doux">
            {t("year")}
          </label>
          <select
            id={`${id}-year`}
            value={value.year}
            onChange={(event) => onChange({ ...value, year: event.target.value })}
            className={selectClass}
          >
            <option value="">–</option>
            {years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
      </div>
      <p className="text-small text-prune-doux">{t("why")}</p>
    </fieldset>
  );
}
