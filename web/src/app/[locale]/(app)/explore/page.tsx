import { MapTrifold } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { SearchBar } from "@/components/features/search/search-bar";
import { TradeIcon, TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ trade?: string; q?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("explore") };
}

export default function ExplorePage({ params, searchParams }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const { trade, q } = use(searchParams);
  const t = useTranslations("explore");
  const tTrades = useTranslations("trades");
  const selected = TRADES.includes(trade as Trade) ? (trade as Trade) : null;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <SearchBar defaultValue={q ?? ""} />

      <nav aria-label={t("trades")}>
        <ul className="-mx-4 flex [scrollbar-width:none] gap-2 overflow-x-auto px-4 pb-1">
          {TRADES.map((key) => {
            const active = key === selected;
            return (
              <li key={key} className="shrink-0">
                <Link
                  href={active ? "/explore" : { pathname: "/explore", query: { trade: key } }}
                  aria-current={active ? "true" : undefined}
                  className={cn(
                    "inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold",
                    active
                      ? "border-prune bg-prune text-lait"
                      : "border-trait bg-poudre text-prune hover:border-prune-doux",
                  )}
                >
                  <TradeIcon
                    trade={key}
                    size={24}
                    className={active ? undefined : "text-hibiscus"}
                  />
                  {tTrades(key)}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <EmptyState
        icon={<MapTrifold size={48} weight="duotone" />}
        title={selected ? t("emptyTradeTitle", { trade: tTrades(selected) }) : t("emptyTitle")}
        description={t("emptyText")}
        action={
          <div className="flex flex-col items-center gap-3">
            <Button asChild size="lg">
              <Link href="/auth?as=client">{t("notify")}</Link>
            </Button>
            <Link href="/auth?as=pro" className="text-hibiscus min-h-12 py-3 font-bold underline">
              {t("proFirst")}
            </Link>
          </div>
        }
      />
    </div>
  );
}
