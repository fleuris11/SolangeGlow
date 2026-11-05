import {
  GraduationCap,
  MapPin,
  SealCheck,
  Star,
  Trophy,
  Van,
} from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";
import Image from "next/image";

import { TradeLabel } from "@/components/features/trades/trade-label";
import { TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { PriceTag } from "@/components/ui/price-tag";
import type { ProCard as Card } from "@/lib/api/pros";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatDistance } from "@/lib/pros/format";

const isTrade = (key: string): key is Trade => (TRADES as readonly string[]).includes(key);

/** A professional in a list of results: the work first, then who, where, open or not, from how much. */
export function ProCard({ pro }: { pro: Card }) {
  const t = useTranslations("explore.card");
  const locale = useLocale();
  const place = [pro.district, pro.city].filter(Boolean).join(", ");
  const photo = mediaSrc(pro.photo, "medium", "thumb");

  return (
    <Link href={`/${pro.slug}`} className="press group flex h-full gap-3 md:flex-col">
      <span className="bg-poudre rounded-photo relative block size-28 shrink-0 overflow-clip md:aspect-[4/5] md:size-auto md:w-full">
        {photo ? (
          <Image
            src={photo}
            alt=""
            fill
            sizes="(min-width: 1280px) 22vw, (min-width: 768px) 33vw, 112px"
            className="object-cover transition-transform duration-500 ease-out group-hover:scale-[1.03]"
          />
        ) : (
          <span
            aria-hidden
            className="font-display text-display absolute inset-0 flex items-center justify-center"
          >
            {pro.business_name.slice(0, 1).toUpperCase()}
          </span>
        )}
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="font-display text-lead flex items-center gap-1">
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
            <GraduationCap weight="fill" size={20} className="shrink-0" aria-label={t("trained")} />
          )}
          {pro.level === 2 && (
            <Trophy weight="fill" size={20} className="shrink-0" aria-label={t("topPro")} />
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
            <MapPin aria-hidden size={16} className="shrink-0" />
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
          <span className={pro.open_now ? "text-feuille font-semibold" : "text-prune-doux"}>
            {pro.open_now ? t("open") : t("closed")}
          </span>
          {pro.rating_average !== null && pro.rating_count > 0 && (
            <span className="inline-flex items-center gap-1">
              <Star aria-hidden size={16} weight="fill" />
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
