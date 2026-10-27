import { GraduationCap, MapPin, SealCheck, Star, Van } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import { TradeLabel } from "@/components/features/trades/trade-label";
import { TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Avatar } from "@/components/ui/avatar";
import { PriceTag } from "@/components/ui/price-tag";
import type { ProCard as Card } from "@/lib/api/pros";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatDistance } from "@/lib/pros/format";

const isTrade = (key: string): key is Trade => (TRADES as readonly string[]).includes(key);

/** A pro in a list of results: who, what, where, open or not, from how much. */
export function ProCard({ pro }: { pro: Card }) {
  const t = useTranslations("explore.card");
  const locale = useLocale();
  const place = [pro.district, pro.city].filter(Boolean).join(", ");

  return (
    <Link
      href={`/${pro.slug}`}
      className="border-trait bg-carte rounded-card hover:border-prune-doux flex gap-4 border p-4"
    >
      <Avatar name={pro.business_name} src={mediaSrc(pro.photo, "thumb", "medium")} size="lg" />
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-lead flex items-center gap-1 font-bold">
          <span className="truncate">{pro.business_name}</span>
          {pro.verified && (
            <SealCheck
              weight="fill"
              size={20}
              className="text-feuille shrink-0"
              aria-label={t("verified")}
            />
          )}
          {pro.trained && (
            <GraduationCap
              weight="fill"
              size={20}
              className="text-or shrink-0"
              aria-label={t("trained")}
            />
          )}
        </span>
        <span className="flex flex-wrap gap-x-3">
          {pro.trades
            .filter((trade) => isTrade(trade.key))
            .slice(0, 2)
            .map((trade) => (
              <TradeLabel key={trade.key} trade={trade.key as Trade} className="text-small" />
            ))}
        </span>
        <span className="text-small text-prune-doux flex flex-wrap items-center gap-x-3">
          <span className="inline-flex items-center gap-1">
            <MapPin aria-hidden size={16} />
            {pro.distance_m !== null
              ? t("distance", { distance: formatDistance(pro.distance_m, locale), place })
              : place}
          </span>
          {pro.travels_to_clients && (
            <span className="inline-flex items-center gap-1">
              <Van aria-hidden size={16} />
              {t("atHome")}
            </span>
          )}
        </span>
        <span className="text-small flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className={pro.open_now ? "text-feuille font-bold" : "text-prune-doux"}>
            {pro.open_now ? t("open") : t("closed")}
          </span>
          {pro.rating_average !== null && pro.rating_count > 0 && (
            <span className="inline-flex items-center gap-1">
              <Star aria-hidden size={16} weight="fill" className="text-or" />
              {t("rating", {
                rating: pro.rating_average.toLocaleString(locale, { maximumFractionDigits: 1 }),
                count: pro.rating_count,
              })}
            </span>
          )}
          {pro.min_price !== null && (
            <PriceTag amountMinor={pro.min_price} currency={pro.currency} prefix={t("from")} />
          )}
        </span>
      </span>
    </Link>
  );
}
