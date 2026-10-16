import { AirplaneTilt, Gift, Scissors, ShoppingBag, Sparkle } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { PriceTag } from "@/components/ui/price-tag";
import type { SelectionSummary } from "@/lib/api/selection";
import { DEMO_GIFT } from "@/lib/demo/data";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

/** "Sélection France": trendy products chosen in France, final price with delivery and customs. */
export function FranceSelectionBand({ products }: { products: SelectionSummary[] }) {
  const t = useTranslations("home.france");
  const tAisles = useTranslations("selection.aisles");
  return (
    <section
      aria-labelledby="france-title"
      className="bg-poudre rounded-card flex flex-col gap-4 p-5"
    >
      <div className="flex items-start gap-3">
        <AirplaneTilt aria-hidden size={32} weight="duotone" className="text-hibiscus shrink-0" />
        <div>
          <h2 id="france-title" className="text-title font-bold">
            {t("title")}
          </h2>
          <p className="text-prune-doux">{t("subtitle")}</p>
        </div>
      </div>
      {products.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-3">
          {products.map((product) => (
            <li key={product.id}>
              <Link
                href={`/selection/${product.slug}`}
                className="bg-carte rounded-card flex items-center gap-3 p-3 sm:flex-col sm:items-start"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
                <img
                  src={mediaSrc(product.photo, "thumb", "medium")}
                  alt=""
                  loading="lazy"
                  width={64}
                  height={64}
                  className="petal bg-poudre size-16 shrink-0 object-cover"
                />
                <span className="flex min-w-0 flex-col">
                  <span className="text-mention text-prune-doux font-bold">
                    {tAisles(product.aisle)}
                  </span>
                  <span className="font-bold">{product.title}</span>
                  <PriceTag amountMinor={product.price_xof} currency="XOF" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="text-small text-prune-doux">{t("promise")}</p>
      <Button asChild variant="secondary" className="self-start">
        <Link href="/selection">
          <ShoppingBag aria-hidden size={22} weight="bold" />
          {t("cta")}
        </Link>
      </Button>
    </section>
  );
}

/** Diaspora: offer a beauty service to a loved one back home, paid in euros. */
export function GiftBand() {
  const t = useTranslations("home.gift");
  return (
    <section
      aria-labelledby="gift-title"
      className="border-or bg-carte rounded-card flex flex-col gap-3 border-2 p-5"
    >
      <Gift aria-hidden size={36} weight="duotone" className="text-hibiscus" />
      <h2 id="gift-title" className="text-title font-bold">
        {t("title")}
      </h2>
      <p>{t("text", { city: DEMO_GIFT.city })}</p>
      <p className="text-prune-doux">
        <PriceTag
          amountMinor={DEMO_GIFT.fromAmountMinor}
          currency={DEMO_GIFT.currency}
          prefix={t("from")}
        />
      </p>
      <Button asChild variant="secondary" className="self-start">
        <Link href="/auth?as=client">
          <Gift aria-hidden size={22} weight="bold" />
          {t("cta")}
        </Link>
      </Button>
    </section>
  );
}

/** The clear invitation to join, as a client or as a pro. */
export function JoinBand() {
  const t = useTranslations("home.join");
  return (
    <section aria-labelledby="join-title" className="flex flex-col gap-4">
      <h2 id="join-title" className="font-display text-headline font-black">
        {t("title")}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <Link
          href="/auth?as=client"
          className="bg-hibiscus text-sur-hibiscus rounded-card flex min-h-32 flex-col justify-between gap-4 p-5"
        >
          <Sparkle aria-hidden size={36} weight="fill" />
          <span>
            <span className="text-lead block font-bold">{t("clientTitle")}</span>
            <span className="block">{t("clientText")}</span>
          </span>
        </Link>
        <Link
          href="/auth?as=pro"
          className="border-prune text-prune hover:bg-poudre rounded-card flex min-h-32 flex-col justify-between gap-4 border-2 p-5"
        >
          <Scissors aria-hidden size={36} weight="duotone" className="text-hibiscus" />
          <span>
            <span className="text-lead block font-bold">{t("proTitle")}</span>
            <span className="text-prune-doux block">{t("proText")}</span>
          </span>
        </Link>
      </div>
    </section>
  );
}
