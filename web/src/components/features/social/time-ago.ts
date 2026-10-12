/** « il y a 2 h », « 3 days ago »: the age of a post or a comment. */
export function timeAgo(iso: string, locale: string, now = Date.now()): string {
  const format = new Intl.RelativeTimeFormat(locale, { numeric: "auto", style: "short" });
  const minutes = Math.round((new Date(iso).getTime() - now) / 60_000);
  if (Math.abs(minutes) < 60) return format.format(Math.min(minutes, 0), "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return format.format(hours, "hour");
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 7) return format.format(days, "day");
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(new Date(iso));
}
