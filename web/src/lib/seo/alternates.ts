import { routing } from "@/lib/i18n/routing";

export const SITE_URL = (process.env.SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");

/** Canonical link and the same page in every language (hreflang), for a path without locale. */
export function alternatesFor(locale: string, path: string) {
  const clean = path === "/" ? "" : path;
  return {
    canonical: `${SITE_URL}/${locale}${clean}`,
    languages: {
      ...Object.fromEntries(routing.locales.map((code) => [code, `${SITE_URL}/${code}${clean}`])),
      "x-default": `${SITE_URL}/${routing.defaultLocale}${clean}`,
    },
  };
}
