"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import Image from "next/image";
import { useState, type ReactNode } from "react";

import { Sheet } from "@/components/ui/sheet";
import { getMyPro, myProQueryKey } from "@/lib/api/pros";
import { useMe } from "@/lib/auth/use-me";
import { cn } from "@/lib/cn";
import { Link, usePathname } from "@/lib/i18n/navigation";

import { AudioToggle } from "../audio-toggle";
import { NotificationBell } from "../notification-bell";
import { SignOutButton } from "../sign-out-button";
import { activeProKey, PRO_BAR, PRO_NAV, STAFF_NAV, type ProNavKey } from "./pro-nav";

const MessagesBadge = dynamic(() => import("../messages-badge").then((m) => m.MessagesBadge));

export type ProChromeIcons = {
  nav: Record<ProNavKey, ReactNode>;
  more: ReactNode;
  see: ReactNode;
  book: ReactNode;
  client: ReactNode;
  signOut: ReactNode;
};

/** What the menu needs to know about her: her salon, or a collaborator's smaller menu. */
function useProSpace() {
  const { data: me } = useMe();
  const owner = !!me?.roles.includes("pro");
  const { data: pro } = useQuery({
    queryKey: myProQueryKey,
    queryFn: getMyPro,
    enabled: owner,
    staleTime: 60_000,
    retry: false,
  });
  const items = owner ? PRO_NAV : PRO_NAV.filter(({ key }) => STAFF_NAV.includes(key));
  return { signedIn: !!me, owner, pro, items };
}

function NavList({
  items,
  icons,
  onChoose,
}: {
  items: typeof PRO_NAV;
  icons: ProChromeIcons;
  onChoose?: () => void;
}) {
  const t = useTranslations("proSpace.nav");
  const pathname = usePathname();
  const active = activeProKey(pathname);
  const { signedIn } = useProSpace();
  return (
    <ul className="flex flex-col gap-1">
      {items.map(({ key, href }) => (
        <li key={key}>
          <Link
            href={href}
            onClick={onChoose}
            aria-current={active === key ? "page" : undefined}
            className={cn(
              "flex min-h-12 items-center gap-3 rounded-lg px-3 font-semibold",
              active === key ? "bg-poudre text-prune" : "text-prune hover:bg-poudre",
            )}
          >
            <span aria-hidden className={cn("inline-flex", active === key && "text-hibiscus")}>
              {icons.nav[key]}
            </span>
            {t(key)}
            {signedIn && key === "messages" && <MessagesBadge layout="row" />}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Her page, the client side and signing out: always visible, never buried in settings. */
function Leave({ icons, slug }: { icons: ProChromeIcons; slug?: string | null }) {
  const t = useTranslations("proSpace");
  return (
    <div className="border-trait flex flex-col gap-1 border-t pt-3">
      {slug && (
        <Link
          href={`/${slug}`}
          className="hover:bg-poudre flex min-h-12 items-center gap-3 rounded-lg px-3 font-semibold"
        >
          {icons.see}
          {t("seeMyPage")}
        </Link>
      )}
      <Link
        href="/"
        className="hover:bg-poudre flex min-h-12 items-center gap-3 rounded-lg px-3 font-semibold"
      >
        {icons.client}
        {t("clientMode")}
      </Link>
      <SignOutButton icon={icons.signOut} className="text-alerte" />
    </div>
  );
}

export function ProSidebar({ icons }: { icons: ProChromeIcons }) {
  const t = useTranslations("proSpace");
  const tMeta = useTranslations("metadata");
  const { pro, items } = useProSpace();
  return (
    <aside className="border-trait bg-lait fixed inset-y-0 left-0 z-30 hidden w-[272px] flex-col gap-3 border-r p-4 lg:flex">
      <div className="flex items-center justify-between gap-2">
        <Link href="/pro" className="shrink-0">
          <Image src="/icons/logo.png" alt={tMeta("title")} width={100} height={49} />
        </Link>
        <span className="bg-prune text-lait text-mention rounded px-2 py-1 font-bold">
          {t("badge")}
        </span>
      </div>
      {pro && <p className="font-display text-title px-3 break-words">{pro.business_name}</p>}
      {/* The menu scrolls on a short screen: leaving always stays in sight. */}
      <nav aria-label={t("menu")} className="min-h-0 flex-1 overflow-y-auto">
        <NavList items={items} icons={icons} />
      </nav>
      <div className="flex shrink-0 items-center gap-1 px-1">
        <NotificationBell layout="row" />
        <AudioToggle compact />
      </div>
      <div className="shrink-0">
        <Leave icons={icons} slug={pro?.slug} />
      </div>
    </aside>
  );
}

export function ProHeader({ icons }: { icons: ProChromeIcons }) {
  const t = useTranslations("proSpace");
  const { pro } = useProSpace();
  return (
    <header className="bg-lait border-trait sticky top-0 z-30 border-b lg:hidden">
      <div className="flex items-center gap-1 px-3 py-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="text-mention text-prune-doux font-bold">{t("badge")}</span>
          <span className="truncate font-bold">{pro?.business_name ?? ""}</span>
        </div>
        {pro?.slug && (
          <Link
            href={`/${pro.slug}`}
            className="text-mention hover:bg-poudre inline-flex min-h-12 min-w-14 flex-col items-center justify-center rounded-lg font-semibold"
          >
            {icons.see}
            <span>{t("myPage")}</span>
          </Link>
        )}
        <AudioToggle compact />
        <NotificationBell />
      </div>
    </header>
  );
}

export function ProBottomBar({ icons }: { icons: ProChromeIcons }) {
  const t = useTranslations("proSpace");
  const tNav = useTranslations("proSpace.nav");
  const pathname = usePathname();
  const active = activeProKey(pathname);
  const { signedIn, pro, items } = useProSpace();
  const [more, setMore] = useState(false);
  const bar = items.filter(({ key }) => PRO_BAR.includes(key));
  const inBar = bar.some(({ key }) => key === active);
  return (
    <>
      <nav
        aria-label={t("menu")}
        className="bg-carte border-trait pb-safe fixed inset-x-0 bottom-0 z-40 border-t lg:hidden"
      >
        <ul className="grid" style={{ gridTemplateColumns: `repeat(${bar.length + 1}, 1fr)` }}>
          {bar.map(({ key, href }) => (
            <li key={key}>
              <Link
                href={href}
                aria-current={active === key ? "page" : undefined}
                className={cn(
                  "text-mention relative flex min-h-16 flex-col items-center justify-center gap-0.5 font-semibold",
                  active === key ? "text-hibiscus" : "text-prune-doux",
                )}
              >
                <span aria-hidden className="inline-flex">
                  {icons.nav[key]}
                </span>
                {tNav(key)}
                {signedIn && key === "messages" && <MessagesBadge layout="icon" />}
              </Link>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() => setMore(true)}
              aria-expanded={more}
              className={cn(
                "text-mention flex min-h-16 w-full flex-col items-center justify-center gap-0.5 font-semibold",
                !inBar && active ? "text-hibiscus" : "text-prune-doux",
              )}
            >
              <span aria-hidden className="inline-flex">
                {icons.more}
              </span>
              {t("more")}
            </button>
          </li>
        </ul>
      </nav>
      <Sheet open={more} onOpenChange={setMore} title={pro?.business_name ?? t("menu")}>
        <div className="flex flex-col gap-3">
          <NavList items={items} icons={icons} onChoose={() => setMore(false)} />
          {/* Leaving stays in sight, however long the menu. */}
          <div className="bg-carte sticky bottom-0">
            <Leave icons={icons} slug={pro?.slug} />
          </div>
        </div>
      </Sheet>
    </>
  );
}
