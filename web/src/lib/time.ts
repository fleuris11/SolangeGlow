/** A time of day the way people say it: "14 h", "14 h 30" (fr), "2:30 PM" (en), "14:30" (sk). */
export function formatTimeOfDay(hour: number, minute: number, locale: string): string {
  if (locale === "fr") {
    return minute === 0 ? `${hour} h` : `${hour} h ${String(minute).padStart(2, "0")}`;
  }
  const date = new Date(Date.UTC(2000, 0, 1, hour, minute));
  return new Intl.DateTimeFormat(locale, {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date);
}
