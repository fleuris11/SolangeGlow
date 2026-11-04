export type ProNavKey =
  | "today"
  | "agenda"
  | "services"
  | "slots"
  | "page"
  | "shop"
  | "clients"
  | "messages"
  | "money"
  | "stats"
  | "plan"
  | "settings";

export type ProNavItem = { key: ProNavKey; href: string };

/** The menu of a pro, in the order of her day: appointments and shop come first. */
export const PRO_NAV: ProNavItem[] = [
  { key: "today", href: "/pro" },
  { key: "agenda", href: "/pro/agenda" },
  { key: "services", href: "/pro/services" },
  { key: "slots", href: "/pro/creneaux" },
  { key: "shop", href: "/pro/shop" },
  { key: "page", href: "/pro/ma-page" },
  { key: "clients", href: "/pro/agenda/clients" },
  { key: "messages", href: "/messages" },
  { key: "money", href: "/pro/wallet" },
  { key: "stats", href: "/pro/dashboard" },
  { key: "plan", href: "/pro/plan" },
  { key: "settings", href: "/pro/agenda/settings" },
];

/** A collaborator only works in her own agenda. */
export const STAFF_NAV: ProNavKey[] = ["agenda", "messages"];

/** Always under the thumb on a phone; the rest is one tap away in « Plus ». */
export const PRO_BAR: ProNavKey[] = ["today", "agenda", "shop", "messages"];

/** The entry of the current page: the longest address that matches. */
export function activeProKey(pathname: string): ProNavKey | undefined {
  return PRO_NAV.filter(
    ({ href }) => pathname === href || (href !== "/pro" && pathname.startsWith(`${href}/`)),
  ).sort((a, b) => b.href.length - a.href.length)[0]?.key;
}
