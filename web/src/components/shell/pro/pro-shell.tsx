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
  Broadcast,
  Gift,
  GraduationCap,
  IdentificationCard,
  Megaphone,
  Package,
  PaperPlaneTilt,
  PlusCircle,
  QrCode,
  Receipt,
  Stack,
  Star,
} from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { ProNavKey } from "./pro-nav";
import { ProBottomBar, ProHeader, ProSidebar, type ProChromeIcons } from "./pro-chrome";
import { SpaceMark } from "@/lib/navigation/space";

const SHAPES: Record<ProNavKey, typeof House> = {
  today: House,
  agenda: CalendarBlank,
  slots: ClockClockwise,
  services: Scissors,
  clients: UserList,
  shop: Storefront,
  stock: Package,
  giftCards: Gift,
  packages: Stack,
  page: Browser,
  share: QrCode,
  publish: PlusCircle,
  lives: Broadcast,
  academy: GraduationCap,
  reviews: Star,
  boost: Megaphone,
  campaigns: PaperPlaneTilt,
  messages: ChatsCircle,
  money: Wallet,
  invoices: Receipt,
  stats: ChartLineUp,
  plan: Crown,
  agendaSettings: GearSix,
  verification: IdentificationCard,
};

/** Icons drawn by the server (ADR-004): the phone receives no icon code. */
function icons(): ProChromeIcons {
  return {
    nav: Object.fromEntries(
      Object.entries(SHAPES).map(([key, Shape]) => [
        key,
        <Shape key={key} aria-hidden size={22} />,
      ]),
    ) as ProChromeIcons["nav"],
    more: <DotsThreeOutline aria-hidden size={22} />,
    see: <Eye aria-hidden size={22} weight="bold" />,
    book: <CalendarCheck aria-hidden size={22} weight="bold" />,
    client: <UserSwitch aria-hidden size={24} />,
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
    <div data-space="pro" className="lg:bg-poudre lg:min-h-svh">
      <a
        href="#main"
        className="bg-rouge text-sur-hibiscus sr-only z-50 rounded-full px-5 py-3 font-bold focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("skipToContent")}
      </a>
      <div>
        <ProSidebar icons={drawn} />
        <div className="min-w-0 lg:py-2 lg:pr-2 lg:pl-[248px]">
          <ProHeader icons={drawn} />
          <div className="lg:bg-lait lg:border-trait lg:min-h-[calc(100svh-1rem)] lg:rounded-2xl lg:border">
            <SpaceMark space="pro" />
            <main
              id="main"
              className="mx-auto w-full max-w-[1180px] px-4 pt-6 pb-32 lg:px-6 lg:pb-12"
            >
              {children}
            </main>
          </div>
        </div>
      </div>
      <ProBottomBar icons={drawn} />
    </div>
  );
}
