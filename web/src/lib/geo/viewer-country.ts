/**
 * The country whose content the person sees (feed, search, lives, courses): found from her time
 * zone on her first visit, changed by her in the city picker. Kept in a cookie so the pages drawn
 * by the server show the same country; sent to the API as X-SG-Country (apps/core/viewer.py).
 * "*" means every country.
 */
export const COUNTRY_COOKIE = "sg_country";
export const EVERYWHERE = "*";
export const COUNTRY_EVENT = "sg:country";

export function readViewerCountry(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)sg_country=([^;]*)/);
  return match ? decodeURIComponent(match[1] ?? "") : "";
}

export function writeViewerCountry(code: string) {
  const value = code === EVERYWHERE ? EVERYWHERE : code.toUpperCase().slice(0, 2);
  document.cookie = `${COUNTRY_COOKIE}=${encodeURIComponent(value)}; Path=/; Max-Age=31536000; SameSite=Lax`;
  window.dispatchEvent(new Event(COUNTRY_EVENT));
}
