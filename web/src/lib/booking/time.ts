/**
 * Times of appointments are shown in the pro's time zone (Cotonou or Paris), whatever the
 * phone's own zone: « 10 h 30 » means 10:30 at the salon.
 */
import { formatTimeOfDay } from "@/lib/time";

export type ZonedParts = { year: number; month: number; day: number; hour: number; minute: number };

const partsCache = new Map<string, Intl.DateTimeFormat>();

function partsFormat(timeZone: string): Intl.DateTimeFormat {
  let found = partsCache.get(timeZone);
  if (!found) {
    found = new Intl.DateTimeFormat("en-GB", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    });
    partsCache.set(timeZone, found);
  }
  return found;
}

/** The wall-clock time of a moment in a time zone. */
export function zonedParts(moment: string | Date, timeZone: string): ZonedParts {
  const date = typeof moment === "string" ? new Date(moment) : moment;
  const values: Record<string, number> = {};
  for (const part of partsFormat(timeZone).formatToParts(date)) {
    if (part.type !== "literal") values[part.type] = Number(part.value);
  }
  return {
    year: values.year ?? 1970,
    month: values.month ?? 1,
    day: values.day ?? 1,
    hour: values.hour ?? 0,
    minute: values.minute ?? 0,
  };
}

/** « 2030-01-07 »: the local day of a moment in the pro's zone. */
export function localDay(moment: string | Date, timeZone: string): string {
  const p = zonedParts(moment, timeZone);
  return `${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`;
}

/** Minutes since local midnight (for the agenda grid). */
export function minutesOfDay(moment: string | Date, timeZone: string): number {
  const p = zonedParts(moment, timeZone);
  return p.hour * 60 + p.minute;
}

/** The moment (ISO, UTC) of a local wall-clock time: « 2030-01-07 », 630 → 10:30 there. */
export function zonedToIso(day: string, minutes: number, timeZone: string): string {
  const [year, month, date] = day.split("-").map(Number) as [number, number, number];
  const wanted = Date.UTC(year, month - 1, date, Math.floor(minutes / 60), minutes % 60);
  // Two passes: the zone's offset can change on that day (summer time).
  let guess = wanted;
  for (let i = 0; i < 2; i++) {
    const p = zonedParts(new Date(guess), timeZone);
    const seen = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
    guess += wanted - seen;
  }
  return new Date(guess).toISOString();
}

/** « 10 h 30 » (fr), « 10:30 AM » (en), « 10:30 » (sk), at the salon. */
export function timeAt(moment: string | Date, timeZone: string, locale: string): string {
  const p = zonedParts(moment, timeZone);
  return formatTimeOfDay(p.hour, p.minute, locale);
}

/** « samedi 11 janvier » for a local day (YYYY-MM-DD). */
export function dayName(day: string, locale: string, short = false): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: short ? "short" : "long",
    day: "numeric",
    month: short ? "short" : "long",
    timeZone: "UTC",
  }).format(new Date(`${day}T12:00:00Z`));
}

/** The weekday (0 = Monday) of a local day, as the backend counts them. */
export function weekdayOf(day: string): number {
  return (new Date(`${day}T12:00:00Z`).getUTCDay() + 6) % 7;
}

export function addDays(day: string, count: number): string {
  const date = new Date(`${day}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + count);
  return date.toISOString().slice(0, 10);
}

/** The Monday of the week of a local day. */
export function mondayOf(day: string): string {
  return addDays(day, -weekdayOf(day));
}

/** « 1 h 30 », « 45 min ». */
export function durationLabel(minutes: number, locale: string): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest} min`;
  if (locale === "fr") return rest ? `${hours} h ${String(rest).padStart(2, "0")}` : `${hours} h`;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}
