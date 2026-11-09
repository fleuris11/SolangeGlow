import { SignOut, Storefront } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { BottomNav } from "@/components/ui/bottom-nav";

import { DesktopSidebar } from "./desktop-sidebar";
import { navIcons } from "./nav-icons";
import { MobileHeader } from "./mobile-header";
import { SpaceMark } from "@/lib/navigation/space";

/**
 * Mobile: header, content, bottom bar.
 * Computer (≥ 1024 px): menu on the left; 640 px for reading, the whole width for a catalogue (data-wide).
 */
export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations("common");
  const icons = navIcons();
  return (
    <>
      <a
        href="#main"
        className="bg-rouge text-sur-hibiscus sr-only z-50 rounded-full px-5 py-3 font-bold focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("skipToContent")}
      </a>
      <div className="lg:grid lg:grid-cols-[232px_minmax(0,1fr)] lg:gap-6 lg:pl-6">
        <DesktopSidebar
          icons={icons}
          leave={{
            pro: <Storefront aria-hidden size={24} />,
            signOut: <SignOut aria-hidden size={24} weight="bold" />,
          }}
        />
        <div className="min-w-0">
          <MobileHeader />
          <SpaceMark space="client" />
          <main
            id="main"
            className="mx-auto w-full max-w-[640px] px-4 pt-6 pb-32 has-[[data-wide]]:max-w-[1240px] lg:pb-16"
          >
            {children}
          </main>
        </div>
      </div>
      <BottomNav icons={icons} />
    </>
  );
}
