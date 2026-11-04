import {
  CalendarBlank,
  CalendarCheck,
  ChartLineUp,
  ChatsCircle,
  ClockClockwise,
  Crown,
  DotsThreeOutline,
  Eye,
  GearSix,
  House,
  Scissors,
  SignOut,
  Storefront,
  UserList,
  UserSwitch,
  Wallet,
  Browser,
} from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { ProNavKey } from "./pro-nav";
import { ProBottomBar, ProHeader, ProSidebar, type ProChromeIcons } from "./pro-chrome";

const SHAPES: Record<ProNavKey, typeof House> = {
  today: House,
  agenda: CalendarBlank,
  services: Scissors,
  slots: ClockClockwise,
  page: Browser,
  shop: Storefront,
  clients: UserList,
  messages: ChatsCircle,
  money: Wallet,
  stats: ChartLineUp,
  plan: Crown,
  settings: GearSix,
};

/** Icons drawn by the server (ADR-004): the phone receives no icon code. */
function icons(): ProChromeIcons {
  return {
    nav: Object.fromEntries(
      Object.entries(SHAPES).map(([key, Shape]) => [
        key,
        <Shape key={key} aria-hidden size={26} weight="duotone" />,
      ]),
    ) as ProChromeIcons["nav"],
    more: <DotsThreeOutline aria-hidden size={26} weight="duotone" />,
    see: <Eye aria-hidden size={22} weight="bold" />,
    book: <CalendarCheck aria-hidden size={22} weight="bold" />,
    client: <UserSwitch aria-hidden size={24} weight="duotone" />,
    signOut: <SignOut aria-hidden size={24} weight="bold" />,
  };
}

/**
 * Mobile: her salon on top, the day under the thumb, everything else in « Plus ».
 * Computer: the menu on the left and a wide page: an agenda needs the room.
 */
export function ProShell({ children }: { children: ReactNode }) {
  const t = useTranslations("common");
  const drawn = icons();
  return (
    <div data-space="pro">
      <a
        href="#main"
        className="bg-rouge text-sur-hibiscus sr-only z-50 rounded-full px-5 py-3 font-bold focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("skipToContent")}
      </a>
      <div>
        <ProSidebar icons={drawn} />
        <div className="min-w-0 lg:pl-[272px]">
          <ProHeader icons={drawn} />
          <main
            id="main"
            className="mx-auto w-full max-w-[1120px] px-4 pt-6 pb-32 lg:px-8 lg:pb-16"
          >
            {children}
          </main>
        </div>
      </div>
      <ProBottomBar icons={drawn} />
    </div>
  );
}
