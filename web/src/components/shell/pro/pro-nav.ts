export type ProNavKey =
  | "today"
  | "agenda"
  | "slots"
  | "services"
  | "clients"
  | "shop"
  | "stock"
  | "giftCards"
  | "packages"
  | "page"
  | "publish"
  | "lives"
  | "boost"
  | "reviews"
  | "share"
  | "academy"
  | "messages"
  | "campaigns"
  | "money"
  | "invoices"
  | "stats"
  | "plan"
  | "agendaSettings"
  | "verification";

export type ProNavItem = { key: ProNavKey; href: string };
export type ProNavGroup = {
  key: "main" | "groupAppointments" | "groupShop" | "groupPresence" | "groupMoney" | "groupMore";
  items: ProNavItem[];
};

/** The menu of her activity, in the order of her day: appointments and shop come first. */
export const PRO_GROUPS: ProNavGroup[] = [
  {
    key: "main",
    items: [
      { key: "today", href: "/pro" },
      { key: "messages", href: "/messages" },
    ],
  },
  {
    key: "groupAppointments",
    items: [
      { key: "agenda", href: "/pro/agenda" },
      { key: "slots", href: "/pro/creneaux" },
      { key: "services", href: "/pro/services" },
      { key: "clients", href: "/pro/agenda/clients" },
    ],
  },
  {
    key: "groupShop",
    items: [
      { key: "shop", href: "/pro/shop" },
      { key: "stock", href: "/pro/stock" },
      { key: "giftCards", href: "/pro/gift-cards" },
      { key: "packages", href: "/pro/packages" },
    ],
  },
  {
    key: "groupPresence",
    items: [
      { key: "page", href: "/pro/ma-page" },
      { key: "share", href: "/pro/share" },
      { key: "publish", href: "/create" },
      { key: "lives", href: "/pro/lives" },
      { key: "academy", href: "/pro/academy" },
      { key: "reviews", href: "/pro/reviews" },
      { key: "boost", href: "/pro/boost" },
      { key: "campaigns", href: "/pro/campaigns" },
    ],
  },
  {
    key: "groupMoney",
    items: [
      { key: "money", href: "/pro/wallet" },
      { key: "invoices", href: "/pro/invoices" },
      { key: "stats", href: "/pro/dashboard" },
    ],
  },
  {
    key: "groupMore",
    items: [
      { key: "plan", href: "/pro/plan" },
      { key: "agendaSettings", href: "/pro/agenda/settings" },
      { key: "verification", href: "/pro/verification" },
    ],
  },
];

export const PRO_NAV: ProNavItem[] = PRO_GROUPS.flatMap((group) => group.items);

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
