import {
  ChatsCircle,
  Compass,
  House,
  PlusCircle,
  UserCircle,
  type Icon,
} from "@phosphor-icons/react";

export type NavKey = "home" | "explore" | "create" | "messages" | "me";

export type NavItem = { key: NavKey; href: string; icon: Icon };

/** The five entries of the app, in the order of the bottom bar. */
export const NAV_ITEMS: NavItem[] = [
  { key: "home", href: "/", icon: House },
  { key: "explore", href: "/explore", icon: Compass },
  { key: "create", href: "/create", icon: PlusCircle },
  { key: "messages", href: "/messages", icon: ChatsCircle },
  { key: "me", href: "/me", icon: UserCircle },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
