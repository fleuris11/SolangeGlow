import { CaretRight, Star } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import { Portrait } from "@/components/features/illustrations/portrait";
import { TradeLabel } from "@/components/features/trades/trade-label";
import { Avatar } from "@/components/ui/avatar";
import { PriceTag } from "@/components/ui/price-tag";
import { DEMO_PROS } from "@/lib/demo/data";
import { Link } from "@/lib/i18n/navigation";
import { formatTimeOfDay } from "@/lib/time";

/**
 * The memorable piece of the home page: pros with a free slot today, each in her
 * petal-shaped portrait with the Glow halo, and the time of the slot in big.
 */
export function AvailableToday() {
  const t = useTranslations("home.available");
  const locale = useLocale();

  return (
    <section aria-labelledby="available-title" className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 id="available-title" className="text-title font-bold">
            {t("title")}
          </h2>
          <p className="text-prune-doux">{t("subtitle")}</p>
        </div>
        <Link
          href="/explore"
          className="text-hibiscus inline-flex min-h-12 shrink-0 items-center gap-1 font-bold"
        >
          {t("seeAll")}
          <CaretRight aria-hidden size={18} weight="bold" />
        </Link>
      </div>

      <ul className="-mx-4 flex snap-x snap-mandatory [scrollbar-width:none] gap-3 overflow-x-auto px-4 pb-2">
        {DEMO_PROS.map((pro) => (
          <li key={pro.id} className="snap-start">
            <Link
              href={{ pathname: "/explore", query: { trade: pro.trade } }}
              className="border-trait bg-carte rounded-card flex w-40 flex-col items-center gap-2 border p-4 text-center"
            >
              <Avatar name={pro.name} size="lg" halo picture={<Portrait {...pro.portrait} />} />
              <span className="text-lead font-bold">{pro.name}</span>
              <TradeLabel trade={pro.trade} className="text-small" />
              <span className="text-small text-prune-doux">{pro.district}</span>
              <span className="bg-poudre mt-1 flex w-full flex-col rounded-2xl px-2 py-2">
                <span className="text-mention text-prune-doux">{t("freeAt")}</span>
                <span className="font-display text-headline font-black">
                  {formatTimeOfDay(pro.nextSlot.hour, pro.nextSlot.minute, locale)}
                </span>
              </span>
              <span className="text-small flex items-center gap-1">
                <Star aria-hidden size={16} weight="fill" className="text-or" />
                <span>
                  {t("rating", {
                    rating: pro.rating.toLocaleString(locale),
                    count: pro.reviews,
                  })}
                </span>
              </span>
              <PriceTag
                amountMinor={pro.fromAmountMinor}
                currency={pro.currency}
                prefix={t("from")}
                className="text-small"
              />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
