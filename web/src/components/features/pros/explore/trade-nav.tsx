import { useTranslations } from "next-intl";

import { TradeIcon, TRADES } from "@/components/features/trades/trade-icon";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";

import { toQuery, type Filters } from "./filters";

/** Trades as plain links (no script needed): the other filters are kept. */
export function TradeNav({ filters }: { filters: Filters }) {
  const t = useTranslations("explore");
  const tTrades = useTranslations("trades");
  return (
    <nav aria-label={t("trades")}>
      <ul className="-mx-4 flex [scrollbar-width:none] gap-2 overflow-x-auto px-4 pb-1">
        {TRADES.map((key) => {
          const active = filters.trade === key;
          return (
            <li key={key} className="shrink-0">
              <Link
                href={{
                  pathname: "/explore",
                  query: toQuery({ ...filters, trade: active ? "" : key }),
                }}
                aria-current={active ? "true" : undefined}
                className={cn(
                  "inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold",
                  active
                    ? "border-prune bg-prune text-lait"
                    : "border-trait bg-poudre text-prune hover:border-prune-doux",
                )}
              >
                <TradeIcon trade={key} size={24} className={active ? undefined : "text-hibiscus"} />
                {tTrades(key)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
