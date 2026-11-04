import { useTranslations } from "next-intl";
import Image from "next/image";
import type { ReactNode } from "react";

import { Link } from "@/lib/i18n/navigation";

import { AudioToggle } from "./audio-toggle";
import { SiteAccount } from "./site-account";

/** Around the page of a pro: the platform stays discreet, her work takes the room. */
export function SiteShell({ children }: { children: ReactNode }) {
  const t = useTranslations("common");
  const tSite = useTranslations("proSpace.site");
  const tMeta = useTranslations("metadata");
  return (
    <>
      <a
        href="#main"
        className="bg-rouge text-sur-hibiscus sr-only z-50 rounded-full px-5 py-3 font-bold focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("skipToContent")}
      </a>
      <header className="bg-lait border-trait sticky top-0 z-30 border-b">
        <div className="mx-auto flex max-w-[1120px] items-center justify-between gap-2 px-4 py-1">
          <Link href="/" className="shrink-0">
            <Image src="/icons/logo.png" alt={tMeta("title")} width={82} height={40} />
          </Link>
          <div className="flex min-w-0 items-center gap-1">
            <AudioToggle compact />
            <SiteAccount />
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-[1120px] px-4 pt-6 pb-32 lg:pb-16">
        {children}
      </main>
      <footer className="border-trait text-small text-prune-doux border-t px-4 pt-4 pb-28 lg:pb-6">
        <div className="mx-auto flex max-w-[1120px] flex-wrap items-center gap-x-6">
          <span>{tSite("poweredBy")}</span>
          <Link href="/" className="inline-flex min-h-12 items-center font-semibold">
            {tSite("discover")}
          </Link>
          <Link href="/pour-les-pros" className="inline-flex min-h-12 items-center font-semibold">
            {tSite("forPros")}
          </Link>
          <Link href="/aide" className="inline-flex min-h-12 items-center font-semibold">
            {tSite("help")}
          </Link>
        </div>
      </footer>
    </>
  );
}
