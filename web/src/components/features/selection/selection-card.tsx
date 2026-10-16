import { UsersThree } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { PriceTag } from "@/components/ui/price-tag";
import type { SelectionSummary } from "@/lib/api/selection";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

/** A product of the Selection: picture, name, merchant, final price. */
export function SelectionCard({ product }: { product: SelectionSummary }) {
  const t = useTranslations("selection.card");
  const picture = mediaSrc(product.photo, "medium", "thumb");
  return (
    <Link href={`/selection/${product.slug}`} className="group flex h-full flex-col gap-2">
      <span className="bg-poudre relative block aspect-square overflow-hidden rounded-2xl">
        {picture && (
          // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
          <img
            src={picture}
            alt=""
            loading="lazy"
            width={360}
            height={360}
            className="size-full object-cover"
          />
        )}
        {product.group && (
          <span className="bg-or text-sur-or text-small absolute top-2 left-2 inline-flex items-center gap-1 rounded-full px-2 py-1 font-bold">
            <UsersThree aria-hidden size={16} weight="fill" />
            {t("group")}
          </span>
        )}
      </span>
      <span className="text-small text-prune-doux">{product.merchant_name}</span>
      <span className="line-clamp-2 font-bold group-hover:underline">{product.title}</span>
      <PriceTag amountMinor={product.price_xof} currency="XOF" />
      {!product.available && (
        <span className="text-small text-alerte font-bold">{t("unavailable")}</span>
      )}
    </Link>
  );
}
