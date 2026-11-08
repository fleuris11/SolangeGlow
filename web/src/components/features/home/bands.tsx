import { AirplaneTilt, ShoppingBag } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { SelectionSummary } from "@/lib/api/selection";
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
        <AirplaneTilt aria-hidden size={32} className="shrink-0" />
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
