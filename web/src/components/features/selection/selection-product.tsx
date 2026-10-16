import { ArrowLeft, LockKey, ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { SpeakButton } from "@/components/ui/speak-button";
import type { PickupPoint, SelectionProduct } from "@/lib/api/selection";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { SelectionBuy } from "./selection-buy";

/** A product of the France Selection: final price, choices, shipping with its delay. */
export function SelectionProductView({
  product,
  points,
}: {
  product: SelectionProduct;
  points: PickupPoint[];
}) {
  const t = useTranslations("selection.product");
  const tAisles = useTranslations("selection.aisles");
  return (
    <article className="flex flex-col gap-6">
      <Link
        href={{ pathname: "/selection", query: { aisle: product.aisle } }}
        className="text-prune-doux hover:bg-poudre -ml-2 inline-flex min-h-12 items-center gap-2 self-start rounded-full px-2 font-bold"
      >
        <ArrowLeft aria-hidden size={22} />
        {tAisles(product.aisle)}
      </Link>
      <ul
        aria-label={t("photos")}
        // Scrolled with the arrow keys too (keyboard users).
        tabIndex={0}
        className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4"
      >
        {product.photos.map((photo, index) => (
          <li key={photo.id} className="w-[85%] shrink-0 snap-center sm:w-[60%]">
            {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
            <img
              src={mediaSrc(photo, "large", "medium")}
              alt={index === 0 ? product.title : t("photoN", { n: index + 1 })}
              width={720}
              height={720}
              fetchPriority={index === 0 ? "high" : undefined}
              loading={index === 0 ? undefined : "lazy"}
              className="bg-poudre aspect-square w-full rounded-2xl object-cover"
            />
          </li>
        ))}
      </ul>
      <header className="flex flex-col gap-2">
        <p className="text-small text-prune-doux font-bold">
          {t("from", { merchant: product.merchant_name, category: product.category.name })}
        </p>
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex-1 font-bold">{product.title}</h1>
          <SpeakButton text={[product.title, product.description].filter(Boolean).join(". ")} />
        </div>
      </header>

      <SelectionBuy
        product={product}
        points={points}
        icons={{ lock: <LockKey aria-hidden size={24} weight="bold" /> }}
      />

      <p className="bg-poudre flex items-start gap-3 rounded-2xl p-4">
        <ShieldCheck aria-hidden size={26} weight="duotone" className="text-hibiscus shrink-0" />
        {t("protected")}
      </p>

      {product.description && (
        <section aria-labelledby="description" className="flex flex-col gap-2">
          <h2 id="description" className="text-title font-bold">
            {t("description")}
          </h2>
          <p className="whitespace-pre-line">{product.description}</p>
        </section>
      )}
    </article>
  );
}
