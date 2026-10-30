import {
  Airplane,
  Diamond,
  Fire,
  LockKey,
  MagnifyingGlass,
  Package,
  Tag,
} from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SpeakButton } from "@/components/ui/speak-button";
import type { Schemas } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";

import { shortDate } from "./dates";
import { SelectionCard } from "./selection-card";

type Aisle = Schemas["AisleEnum"];
const AISLES: { key: Aisle; icon: ReactNode }[] = [
  { key: "small_prices", icon: <Tag aria-hidden size={20} weight="duotone" /> },
  { key: "trending", icon: <Fire aria-hidden size={20} weight="duotone" /> },
  { key: "luxury", icon: <Diamond aria-hidden size={20} weight="duotone" /> },
];

/** The France Selection: three aisles, final prices, and the special request. */
export function SelectionHome({
  page,
  aisle,
  sponsored,
}: {
  page: Schemas["SelectionProductList"];
  aisle?: Aisle;
  /** A sponsored product above the shelves (module 12). */
  sponsored?: ReactNode;
}) {
  const t = useTranslations("selection.home");
  const tAisles = useTranslations("selection.aisles");
  const locale = useLocale();
  const grouped = t("delay", {
    from: shortDate(page.grouped.from, locale),
    to: shortDate(page.grouped.to, locale),
  });
  const chip = (active: boolean) =>
    cn(
      "inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold whitespace-nowrap",
      active ? "border-hibiscus bg-hibiscus text-sur-hibiscus" : "border-trait hover:bg-poudre",
    );

  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <div className="flex items-start gap-2">
          <h1 className="font-display text-display flex-1 font-black">{t("title")}</h1>
          <SpeakButton text={`${t("title")}. ${t("intro")}`} />
        </div>
        <p className="text-lead">{t("intro")}</p>
        <ul className="flex flex-col gap-2">
          {[
            [<Tag key="t" aria-hidden size={22} weight="duotone" />, t("finalPrice")],
            [<LockKey key="l" aria-hidden size={22} weight="duotone" />, t("held")],
            [<Airplane key="a" aria-hidden size={22} weight="duotone" />, grouped],
          ].map(([icon, text]) => (
            <li key={String(text)} className="flex items-start gap-2">
              <span className="text-hibiscus mt-0.5 shrink-0">{icon}</span>
              <span>{text}</span>
            </li>
          ))}
        </ul>
      </header>

      <nav aria-label={t("aisles")} className="-mx-4 overflow-x-auto px-4">
        <ul className="flex gap-2">
          <li>
            <Link
              href="/selection"
              className={chip(!aisle)}
              aria-current={!aisle ? "page" : undefined}
            >
              {t("all")}
            </Link>
          </li>
          {AISLES.map((item) => (
            <li key={item.key}>
              <Link
                href={{ pathname: "/selection", query: { aisle: item.key } }}
                className={chip(aisle === item.key)}
                aria-current={aisle === item.key ? "page" : undefined}
              >
                {item.icon}
                {tAisles(item.key)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {sponsored}

      {page.results.length === 0 ? (
        <EmptyState
          icon={<Package size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3">
          {page.results.map((product) => (
            <li key={product.id}>
              <SelectionCard product={product} />
            </li>
          ))}
        </ul>
      )}

      <section
        aria-labelledby="special"
        className="bg-poudre rounded-card flex flex-col items-start gap-3 p-5"
      >
        <h2 id="special" className="text-title flex items-center gap-2 font-bold">
          <MagnifyingGlass aria-hidden size={26} weight="duotone" className="text-hibiscus" />
          {t("specialTitle")}
        </h2>
        <p>{t("specialText")}</p>
        <Link href="/selection/requests" className={buttonClasses({ size: "lg" })}>
          {t("specialCta")}
        </Link>
      </section>

      <Link href="/selection/orders" className="text-hibiscus self-start font-bold underline">
        {t("myOrders")}
      </Link>
    </article>
  );
}
