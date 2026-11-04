"use client";

import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { searchCities } from "@/lib/api/geo";
import { cn } from "@/lib/cn";

type City = Awaited<ReturnType<typeof searchCities>>[number];

/**
 * Type the first letters, choose a city. A place that is not listed can simply be typed:
 * nobody is stopped because a village is missing.
 */
export function CityField({
  label,
  value,
  onChange,
  country,
  onPick,
  autoFocus,
  showCountry = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  country?: string;
  onPick?: (city: City) => void;
  autoFocus?: boolean;
  showCountry?: boolean;
}) {
  const t = useTranslations("geo");
  const inputId = useId();
  const listId = useId();
  const [found, setFound] = useState<City[]>([]);
  const [open, setOpen] = useState(false);
  const skip = useRef(false);

  useEffect(() => {
    if (skip.current) {
      skip.current = false;
      return;
    }
    if (value.trim().length < 2) return;
    const stop = new AbortController();
    const wait = setTimeout(() => {
      searchCities(value.trim(), country, stop.signal)
        .then((rows) => {
          setFound(rows);
          setOpen(true);
        })
        .catch(() => setFound([]));
    }, 200);
    return () => {
      clearTimeout(wait);
      stop.abort();
    };
  }, [value, country]);

  const shown = value.trim().length >= 2 ? found : [];
  const choose = (city: City) => {
    skip.current = true;
    onChange(city.name);
    onPick?.(city);
    setOpen(false);
  };

  return (
    <div className="relative flex flex-col gap-2">
      <label htmlFor={inputId} className="font-bold">
        {label}
      </label>
      <input
        id={inputId}
        role="combobox"
        aria-expanded={open && shown.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        autoFocus={autoFocus}
        value={value}
        maxLength={80}
        placeholder={t("placeholder")}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="border-trait bg-carte rounded-field focus:border-hibiscus min-h-12 w-full border-2 px-3 outline-none"
      />
      <ul
        id={listId}
        role="listbox"
        aria-label={label}
        className={cn(
          "bg-carte border-trait rounded-field absolute top-full z-20 mt-1 max-h-64 w-full overflow-y-auto border shadow-lg",
          !(open && shown.length > 0) && "hidden",
        )}
      >
        {shown.map((city) => (
          <li
            key={`${city.country}-${city.name}-${city.postal_code}`}
            role="option"
            aria-selected={city.name === value}
          >
            <button
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(city)}
              className="hover:bg-poudre flex min-h-12 w-full flex-col justify-center px-3 py-2 text-left"
            >
              <span className="font-semibold">{city.name}</span>
              <span className="text-small text-prune-doux">
                {[city.postal_code, showCountry || !country ? city.country_name : ""]
                  .filter(Boolean)
                  .join(", ")}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
