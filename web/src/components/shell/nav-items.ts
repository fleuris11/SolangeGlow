export type NavKey = "home" | "explore" | "create" | "messages" | "me";

export type NavItem = { key: NavKey; href: string };

/** The five entries of the app, in the order of the bottom bar (icons: ./nav-icons). */
export const NAV_ITEMS: NavItem[] = [
  { key: "home", href: "/" },
  { key: "explore", href: "/explore" },
  { key: "create", href: "/create" },
  { key: "messages", href: "/messages" },
  { key: "me", href: "/me" },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
