import {
  ChatsCircle,
  Compass,
  House,
  PlusCircle,
  UserCircle,
} from "@phosphor-icons/react/dist/ssr";
import type { ReactNode } from "react";

import type { NavKey } from "./nav-items";

export type NavIcons = Record<NavKey, { on: ReactNode; off: ReactNode }>;

const SHAPES = {
  home: House,
  explore: Compass,
  create: PlusCircle,
  messages: ChatsCircle,
  me: UserCircle,
};

/**
 * The menu icons, drawn by the server in both states (current page or not): the phone
 * receives no icon code (ADR-004, each client icon weighs 1 to 2 KB).
 */
export function navIcons(): NavIcons {
  return Object.fromEntries(
    Object.entries(SHAPES).map(([key, Shape]) => [
      key,
      {
        on: <Shape aria-hidden size={28} weight="fill" />,
        off: <Shape aria-hidden size={28} weight="duotone" />,
      },
    ]),
  ) as NavIcons;
}
