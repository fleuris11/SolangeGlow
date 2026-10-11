import { formatTimeOfDay } from "@/lib/time";

/** Weekday of the API (0 = Monday … 6 = Sunday) in the language of the page. */
export function weekdayName(weekday: number, locale: string, style: "long" | "short" = "long") {
  // 1 January 2024 was a Monday.
  const date = new Date(Date.UTC(2024, 0, 1 + weekday));
  const name = new Intl.DateTimeFormat(locale, { weekday: style, timeZone: "UTC" }).format(date);
  return name.charAt(0).toUpperCase() + name.slice(1);
}

/** "08:00" from the API → "8 h" (fr), "8:00 AM" (en). */
export function formatClock(value: string, locale: string): string {
  const [hour = "0", minute = "0"] = value.split(":");
  return formatTimeOfDay(Number(hour), Number(minute), locale);
}

/** A moment in the pro's time zone: "lundi 8 h" (or just "8 h" when it is today). */
export function formatMoment(iso: string, timeZone: string, locale: string, today = new Date()) {
  const date = new Date(iso);
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    weekday: "short",
    hourCycle: "h23",
  }).formatToParts(date);
  const hour = Number(parts.find((p) => p.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? 0);
  const time = formatTimeOfDay(hour, minute, locale);
  const sameDay =
    new Intl.DateTimeFormat("en-CA", { timeZone, dateStyle: "short" }).format(date) ===
    new Intl.DateTimeFormat("en-CA", { timeZone, dateStyle: "short" }).format(today);
  if (sameDay) return time;
  const day = new Intl.DateTimeFormat(locale, { weekday: "long", timeZone }).format(date);
  return `${day} ${time}`;
}

/** "800 m", "2,6 km", "12 km". */
export function formatDistance(meters: number, locale: string): string {
  if (meters < 1000) {
    const rounded = Math.max(50, Math.round(meters / 50) * 50);
    return new Intl.NumberFormat(locale, { style: "unit", unit: "meter" }).format(rounded);
  }
  const km = meters / 1000;
  return new Intl.NumberFormat(locale, {
    style: "unit",
    unit: "kilometer",
    maximumFractionDigits: km < 10 ? 1 : 0,
  }).format(km);
}

/** Splits minutes for the « duration » message: { hours, minutes }. */
export function durationParts(total: number) {
  return { hours: Math.floor(total / 60), minutes: total % 60 };
}

/** Today's weekday (0 = Monday) in the pro's time zone. */
export function weekdayIn(timeZone: string, now = new Date()): number {
  const short = new Intl.DateTimeFormat("en-US", { weekday: "short", timeZone }).format(now);
  return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(short);
}
