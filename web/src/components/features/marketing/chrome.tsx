import { useTranslations } from "next-intl";
import Image from "next/image";
import type { ReactNode } from "react";

import { AudioToggle } from "@/components/shell/audio-toggle";
import { navIcons } from "@/components/shell/nav-icons";
import { BottomNav } from "@/components/ui/bottom-nav";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { Link } from "@/lib/i18n/navigation";

export const TITLE = "font-display min-w-0 text-balance hyphens-none [overflow-wrap:anywhere]";

/** A group of short lines kept as an object in the messages, in order. */
export function lines(t: { raw: (key: never) => unknown }, key: string) {
  return Object.values(t.raw(key as never) as Record<string, string>);
}

const CHIP =
  "press bg-lait text-prune hover:bg-poudre rounded-button text-small inline-flex min-h-11 min-w-0 shrink items-center justify-center px-3 text-center leading-tight font-semibold sm:px-4 sm:whitespace-nowrap";

/**
 * Top of the public pages. The links sit on the field of colour; the account stays on small sheets
 * of paper, which remain readable whatever is behind them (a field or a photo).
 */
export function TopBar({ signedIn = false }: { signedIn?: boolean }) {
  const t = useTranslations("marketing");
  return (
    <header className="absolute inset-x-0 top-0 z-20 flex items-center justify-between gap-3 px-4 py-3 md:px-8 xl:px-10 xl:py-5">
      <div className="flex min-w-0 items-center gap-8">
        <Link href="/" aria-label="Solange glow" className="press min-w-16 shrink">
          <Image
            src="/brand/logo-white.png"
            alt="Solange glow"
            width={640}
            height={291}
            sizes="125px"
            className="h-9 w-auto sm:h-11 xl:h-14"
          />
        </Link>
        <nav
          aria-label={t("nav.label")}
          className="text-small hidden items-center gap-6 font-semibold xl:flex"
        >
          <Link href="/#services" className="hover:underline hover:underline-offset-4">
            {t("nav.services")}
          </Link>
          <Link href="/explore" className="hover:underline hover:underline-offset-4">
            {t("nav.explore")}
          </Link>
          <Link href="/selection" className="hover:underline hover:underline-offset-4">
            {t("nav.selection")}
          </Link>
          <Link href="/academie" className="hover:underline hover:underline-offset-4">
            {t("nav.academy")}
          </Link>
          <Link href="/offrir" className="hover:underline hover:underline-offset-4">
            {t("nav.gift")}
          </Link>
        </nav>
      </div>
      <div data-ambiance="papier" className="flex min-w-0 items-center gap-2 bg-transparent!">
        <AudioToggle compact className="bg-lait min-h-11" />
        <Link href="/proposer-mes-services" className={`${CHIP} max-xl:hidden`}>
          {t("nav.pros")}
        </Link>
        {signedIn ? (
          <Link href="/me" className={CHIP}>
            {t("myAccount")}
          </Link>
        ) : (
          <>
            <Link href="/auth" className={CHIP}>
              {t("signIn")}
            </Link>
            <Link href="/auth?as=client" className={`${CHIP} max-sm:hidden`}>
              {t("createAccount")}
            </Link>
          </>
        )}
      </div>
    </header>
  );
}

/** The close of a public page: one quiet line. Everything else is reached from the page itself. */
export function SiteFooter() {
  const t = useTranslations("marketing");
  const year = new Date().getFullYear();
  return (
    <footer className="text-small grid items-center gap-x-6 gap-y-2 px-4 pt-[20svh] pb-28 md:px-8 xl:grid-cols-[1fr_auto_1fr] xl:px-10 xl:pb-8">
      <p className="text-prune-doux">{t("everywhere")}</p>
      <nav aria-label={t("footer.help")} className="flex flex-wrap gap-x-6 font-semibold">
        <Link href="/comment-ca-marche" className="inline-flex min-h-12 items-center">
          {t("nav.how")}
        </Link>
        <Link href="/aide" className="inline-flex min-h-12 items-center">
          {t("footer.helpCentre")}
        </Link>
        <Link href="/pages/conditions-generales" className="inline-flex min-h-12 items-center">
          {t("footer.terms")}
        </Link>
        <Link href="/pages/confidentialite" className="inline-flex min-h-12 items-center">
          {t("footer.privacy")}
        </Link>
        <a href="/media/CREDITS.md" className="inline-flex min-h-12 items-center">
          {t("footer.credits")}
        </a>
      </nav>
      <div className="text-prune-doux flex flex-wrap items-center gap-x-4 xl:justify-end">
        <LocaleSwitcher />
        <span>{year}</span>
      </div>
    </footer>
  );
}

/** A public page without the app menu: skip link, content, footer, and the bar of the phone. */
export function MarketingPage({ children }: { children: ReactNode }) {
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
      <main id="main">{children}</main>
      <SiteFooter />
      <BottomNav icons={icons} />
    </>
  );
}
