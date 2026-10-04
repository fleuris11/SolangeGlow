import { Gift } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { TradeLabel } from "@/components/features/trades/trade-label";
import { Portrait } from "@/components/features/illustrations/portrait";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { PriceTag } from "@/components/ui/price-tag";
import { DEMO_GIFT, DEMO_PROS } from "@/lib/demo/data";
import { Link } from "@/lib/i18n/navigation";

/** Computer layout: suggestions next to the main column. */
export function RightColumn() {
  const t = useTranslations("aside");
  return (
    <aside className="sticky top-0 hidden h-dvh flex-col gap-6 overflow-y-auto py-6 xl:flex">
      <section
        aria-labelledby="aside-pros"
        className="border-trait bg-carte rounded-card border p-5"
      >
        <h2 id="aside-pros" className="text-lead font-bold">
          {t("prosNearby")}
        </h2>
        <ul className="mt-4 flex flex-col gap-4">
          {DEMO_PROS.slice(0, 3).map((pro) => (
            <li key={pro.id}>
              <Link href="/explore" className="rounded-card flex items-center gap-3">
                <Avatar name={pro.name} size="sm" picture={<Portrait {...pro.portrait} />} />
                <span className="flex flex-col">
                  <span className="font-bold">{pro.name}</span>
                  <TradeLabel trade={pro.trade} className="text-small text-prune-doux" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <section aria-labelledby="aside-gift" className="bg-poudre rounded-card p-5">
        <Gift aria-hidden size={32} weight="duotone" className="text-hibiscus" />
        <h2 id="aside-gift" className="text-lead mt-2 font-bold">
          {t("giftTitle")}
        </h2>
        <p className="text-prune-doux mt-1">
          {t("giftText")}{" "}
          <PriceTag
            amountMinor={DEMO_GIFT.fromAmountMinor}
            currency={DEMO_GIFT.currency}
            prefix={t("from")}
          />
        </p>
        <Button asChild variant="secondary" className="mt-4">
          <Link href="/auth?as=client">{t("giftCta")}</Link>
        </Button>
      </section>
    </aside>
  );
}
