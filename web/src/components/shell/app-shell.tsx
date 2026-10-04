import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { BottomNav } from "@/components/ui/bottom-nav";

import { DesktopSidebar } from "./desktop-sidebar";
import { MobileHeader } from "./mobile-header";
import { RightColumn } from "./right-column";

/**
 * Mobile: header, content, bottom bar.
 * Computer (≥ 1024 px): menu on the left, content of 640 px max, suggestions on the right (≥ 1280 px).
 */
export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations("common");
  return (
    <>
      <a
        href="#main"
        className="bg-hibiscus text-sur-hibiscus sr-only z-50 rounded-full px-5 py-3 font-bold focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("skipToContent")}
      </a>
      <div className="lg:grid lg:grid-cols-[220px_minmax(0,640px)] lg:justify-center lg:gap-8 xl:grid-cols-[220px_minmax(0,640px)_300px]">
        <DesktopSidebar />
        <div className="min-w-0">
          <MobileHeader />
          <main id="main" className="mx-auto w-full max-w-[640px] px-4 pt-6 pb-32 lg:pb-16">
            {children}
          </main>
        </div>
        <RightColumn />
      </div>
      <BottomNav />
    </>
  );
}
