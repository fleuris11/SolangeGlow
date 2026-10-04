import { useTranslations } from "next-intl";

import { Link } from "@/lib/i18n/navigation";

import { TradeIcon, TRADES } from "./trade-icon";

/** The seven trades as big petal-shaped tiles in a swipeable row: easy to touch, words never cut. */
export function TradePetals() {
  const t = useTranslations("trades");
  return (
    <ul className="-mx-4 flex snap-x [scrollbar-width:none] gap-2 overflow-x-auto px-4 pb-1">
      {TRADES.map((trade) => (
        <li key={trade} className="w-24 shrink-0 snap-start">
          <Link
            href={{ pathname: "/explore", query: { trade } }}
            className="group text-small rounded-card flex flex-col items-center gap-2 text-center font-bold"
          >
            <span className="petal bg-poudre text-hibiscus group-hover:bg-hibiscus group-hover:text-sur-hibiscus inline-flex size-20 items-center justify-center transition-colors duration-150">
              <TradeIcon trade={trade} size={40} />
            </span>
            <span className="whitespace-nowrap">{t(trade)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
