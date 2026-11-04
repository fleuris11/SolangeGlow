import { useTranslations } from "next-intl";
import Image from "next/image";
import type { ReactNode } from "react";

import { AudioToggle } from "@/components/shell/audio-toggle";
import { navIcons } from "@/components/shell/nav-icons";
import { BottomNav } from "@/components/ui/bottom-nav";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { Link } from "@/lib/i18n/navigation";

export const TITLE = "font-display min-w-0 text-balance hyphens-none [overflow-wrap:anywhere]";

/** A group of short lines kept as an object in the messages, in order. */
export function lines(t: { raw: (key: never) => unknown }, key: string) {
  return Object.values(t.raw(key as never) as Record<string, string>);
}

function Logo({ className, sizes }: { className?: string; sizes: string }) {
  return (
    <Image
      src="/brand/logo-white.png"
      alt="Solange glow"
      width={640}
      height={291}
      sizes={sizes}
      className={className}
    />
  );
}

/** Top of the public pages, over their opening photo: who can sign in stays visible. */
export function TopBar({ signedIn = false }: { signedIn?: boolean }) {
  const t = useTranslations("marketing");
  return (
    <header className="absolute inset-x-0 top-0 z-20 flex items-center justify-between gap-3 px-4 py-3 lg:px-10 lg:py-5">
      <Link href="/" aria-label="Solange glow" className="shrink-0">
        <Logo sizes="125px" className="h-11 w-auto lg:h-14" />
      </Link>
      <nav aria-label={t("nav.label")} className="hidden items-center gap-6 font-semibold xl:flex">
        <Link href="/explore">{t("nav.explore")}</Link>
        <Link href="/selection">{t("nav.selection")}</Link>
        <Link href="/academie">{t("nav.academy")}</Link>
        <Link href="/offrir">{t("nav.gift")}</Link>
        <Link href="/proposer-mes-services">{t("nav.pros")}</Link>
        <Link href="/comment-ca-marche">{t("nav.how")}</Link>
      </nav>
      <div className="flex min-w-0 items-center gap-1 sm:gap-2">
        <AudioToggle compact />
        {signedIn ? (
          <Button
            asChild
            variant="secondary"
            className="text-small min-h-11 min-w-0 shrink px-2 leading-tight sm:px-4 sm:whitespace-nowrap"
          >
            <Link href="/me">{t("myAccount")}</Link>
          </Button>
        ) : (
          <>
            <Button
              asChild
              variant="secondary"
              className="text-small min-h-11 min-w-0 shrink px-2 leading-tight sm:px-4 sm:whitespace-nowrap"
            >
              <Link href="/auth">{t("signIn")}</Link>
            </Button>
            <div className="hidden sm:block">
              <Button
                asChild
                variant="secondary"
                className="text-small min-h-11 min-w-0 shrink px-2 leading-tight sm:px-4 sm:whitespace-nowrap"
              >
                <Link href="/auth?as=client">{t("createAccount")}</Link>
              </Button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}

function FooterColumn({ title, children }: { title: string; children: ReactNode }) {
  return (
    <nav aria-label={title} className="flex flex-col">
      <h2 className="text-small text-prune-doux mb-1 font-semibold">{title}</h2>
      {children}
    </nav>
  );
}

function FooterLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="inline-flex min-h-12 items-center font-semibold">
      {children}
    </Link>
  );
}

/** The map of the site: from here a visitor can reach everything the platform does. */
export function SiteFooter() {
  const t = useTranslations("marketing");
  return (
    <EditorialSection ambiance="nuit" className="px-4 pt-12 pb-28 lg:px-10 lg:pb-12">
      <footer className="flex flex-col gap-10">
        <div className="flex flex-col gap-2">
          <Logo sizes="176px" className="h-16 w-auto self-start lg:h-20" />
          <p className="text-lead text-prune-doux">{t("everywhere")}</p>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-8 lg:grid-cols-4">
          <FooterColumn title={t("footer.forYou")}>
            <FooterLink href="/explore">{t("footer.explore")}</FooterLink>
            <FooterLink href="/selection">{t("nav.selection")}</FooterLink>
            <FooterLink href="/academie">{t("nav.academy")}</FooterLink>
            <FooterLink href="/offrir">{t("footer.gift")}</FooterLink>
            <FooterLink href="/classements">{t("footer.games")}</FooterLink>
          </FooterColumn>
          <FooterColumn title={t("nav.pros")}>
            <FooterLink href="/proposer-mes-services">{t("footer.proTools")}</FooterLink>
            <FooterLink href="/auth?as=pro">{t("footer.proStart")}</FooterLink>
            <FooterLink href="/academie">{t("footer.proTeach")}</FooterLink>
          </FooterColumn>
          <FooterColumn title={t("footer.account")}>
            <FooterLink href="/auth?as=client">{t("createAccount")}</FooterLink>
            <FooterLink href="/auth">{t("signIn")}</FooterLink>
            <FooterLink href="/comment-ca-marche#comptes">{t("footer.accounts")}</FooterLink>
          </FooterColumn>
          <FooterColumn title={t("footer.help")}>
            <FooterLink href="/comment-ca-marche">{t("nav.how")}</FooterLink>
            <FooterLink href="/aide">{t("footer.helpCentre")}</FooterLink>
            <FooterLink href="/pages/conditions-generales">{t("footer.terms")}</FooterLink>
            <FooterLink href="/pages/confidentialite">{t("footer.privacy")}</FooterLink>
            <a href="/media/CREDITS.md" className="inline-flex min-h-12 items-center font-semibold">
              {t("footer.credits")}
            </a>
          </FooterColumn>
        </div>
        <LocaleSwitcher />
      </footer>
    </EditorialSection>
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
