"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { useRouter } from "@/lib/i18n/navigation";
import type { Space } from "@/lib/navigation/space";

import { NAV_ITEMS } from "./nav-items";
import { PRO_NAV } from "./pro/pro-nav";

/** Screens of the client side beyond the five of the menu. */
const CLIENT_MORE = [
  { key: "appointments", href: "/appointments" },
  { key: "orders", href: "/orders" },
  { key: "cart", href: "/cart" },
  { key: "notifications", href: "/notifications" },
  { key: "academy", href: "/academie" },
  { key: "selection", href: "/selection" },
  { key: "gifts", href: "/offrir" },
  { key: "points", href: "/points" },
  { key: "help", href: "/aide" },
] as const;

const plain = (text: string) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function GoToDialog({
  space,
  open,
  onOpenChange,
}: {
  space: Space;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("goTo");
  const tNav = useTranslations("nav");
  const tPro = useTranslations("proSpace.nav");
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);

  const all = useMemo(
    () =>
      space === "pro"
        ? [
            ...PRO_NAV.map((item) => ({ href: item.href, label: tPro(item.key) })),
            { href: "/", label: t("clientSide") },
          ]
        : [
            ...NAV_ITEMS.map((item) => ({ href: item.href, label: tNav(item.key) })),
            ...CLIENT_MORE.map((item) => ({ href: item.href, label: t(`client.${item.key}`) })),
            { href: "/pro", label: t("proSide") },
          ],
    [space, t, tNav, tPro],
  );
  const shown = all.filter((item) => plain(item.label).includes(plain(query.trim())));
  const go = (href: string) => {
    onOpenChange(false);
    router.push(href);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
        <Dialog.Content
          aria-describedby={undefined}
          className="bg-carte rounded-card fixed top-[12vh] left-1/2 z-50 flex max-h-[70vh] w-[min(36rem,calc(100vw-2rem))] -translate-x-1/2 flex-col gap-3 p-4"
        >
          <Dialog.Title className="font-display text-title">{t("title")}</Dialog.Title>
          <input
            autoFocus
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setIndex(0);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setIndex((i) => Math.min(i + 1, shown.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setIndex((i) => Math.max(i - 1, 0));
              } else if (event.key === "Enter" && shown[index]) {
                event.preventDefault();
                go(shown[index].href);
              }
            }}
            aria-label={t("search")}
            placeholder={t("placeholder")}
            className="bg-poudre min-h-12 rounded-xl px-4 text-[1.0625rem] outline-none focus-visible:ring-2"
          />
          {shown.length === 0 ? (
            <p className="text-prune-doux px-1">{t("none")}</p>
          ) : (
            <ul className="flex flex-col overflow-y-auto">
              {shown.map((item, position) => (
                <li key={`${item.href}-${item.label}`}>
                  <button
                    type="button"
                    onClick={() => go(item.href)}
                    onMouseEnter={() => setIndex(position)}
                    className={`flex min-h-12 w-full items-center rounded-lg px-3 text-left font-semibold ${
                      position === index ? "bg-poudre" : ""
                    }`}
                  >
                    {item.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
