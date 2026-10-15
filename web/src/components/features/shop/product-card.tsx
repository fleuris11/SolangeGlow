import { Lightning } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { PriceTag } from "@/components/ui/price-tag";
import type { ProductSummary } from "@/lib/api/shop";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

/** A product in a grid: picture, name, price (and the old one during a flash sale). */
export function ProductCard({ product, shopSlug }: { product: ProductSummary; shopSlug: string }) {
  const t = useTranslations("shop.card");
  const picture = mediaSrc(product.photo, "medium", "thumb");
  return (
    <Link
      href={`/${shopSlug}/shop/${product.slug}`}
      className="group rounded-card flex h-full flex-col gap-2"
    >
      <span className="bg-poudre relative block aspect-square overflow-hidden rounded-2xl">
        {picture && (
          // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
          <img
            src={picture}
            alt=""
            loading="lazy"
            className="size-full object-cover"
            width={360}
            height={360}
          />
        )}
        {product.flash_sale && (
          <span className="bg-hibiscus text-sur-hibiscus text-small absolute top-2 left-2 inline-flex items-center gap-1 rounded-full px-2 py-1 font-bold">
            <Lightning aria-hidden size={16} weight="fill" />
            {t("flash", { percent: product.flash_sale.percent_off })}
          </span>
        )}
      </span>
      <span className="line-clamp-2 font-bold group-hover:underline">{product.title}</span>
      <span className="flex flex-wrap items-baseline gap-x-2">
        <PriceTag amountMinor={product.price_minor} currency={product.currency} />
        {product.before_minor !== null && (
          <s className="text-small text-prune-doux">
            <span className="sr-only">{t("before")} </span>
            <PriceTag
              amountMinor={product.before_minor}
              currency={product.currency}
              className="font-normal"
            />
          </s>
        )}
      </span>
      {!product.in_stock && (
        <span className="text-small text-alerte font-bold">{t("soldOut")}</span>
      )}
    </Link>
  );
}
