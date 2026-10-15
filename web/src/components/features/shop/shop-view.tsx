import { ArrowLeft, Gift, ShoppingBag, Storefront } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PriceTag } from "@/components/ui/price-tag";
import type { ShopPage } from "@/lib/api/shop";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { BundleButton } from "./buy-buttons";
import { DeliveryInfo } from "./delivery-info";
import { ProductCard } from "./product-card";

/** The whole shop of a pro: categories, products, bundles and how she hands over. */
export function ShopView({
  page,
  slug,
  category,
}: {
  page: ShopPage;
  slug: string;
  category?: string;
}) {
  const t = useTranslations("shop.page");
  const currency = page.products[0]?.currency ?? page.bundles[0]?.currency ?? "XOF";
  const chip = (active: boolean) =>
    cn(
      "inline-flex min-h-12 items-center rounded-full border-2 px-4 font-bold whitespace-nowrap",
      active ? "border-hibiscus bg-hibiscus text-sur-hibiscus" : "border-trait hover:bg-poudre",
    );

  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-4">
        <Link
          href={`/${slug}`}
          className="text-prune-doux hover:bg-poudre -ml-2 inline-flex min-h-12 items-center gap-2 self-start rounded-full px-2 font-bold"
        >
          <ArrowLeft aria-hidden size={22} />
          {t("back", { name: page.shop.name })}
        </Link>
        <div className="flex items-center gap-4">
          <Avatar name={page.shop.name} src={mediaSrc(page.shop.photo, "thumb")} size="md" />
          <div className="flex flex-col gap-1">
            <h1 className="text-headline flex items-center gap-2 font-bold">
              <Storefront aria-hidden size={28} weight="duotone" className="text-hibiscus" />
              {t("title", { name: page.shop.name })}
            </h1>
            {page.shop.is_verified && <Badge tone="verified">{t("verified")}</Badge>}
          </div>
        </div>
        {!page.delivery.is_open && (
          <p role="status" className="bg-poudre rounded-2xl p-3 font-bold">
            {t("closed")}
          </p>
        )}
      </header>

      {page.categories.length > 1 && (
        <nav aria-label={t("categories")} className="-mx-4 overflow-x-auto px-4">
          <ul className="flex gap-2">
            <li>
              <Link href={`/${slug}/shop`} className={chip(!category)}>
                {t("all")}
              </Link>
            </li>
            {page.categories.map((item) => (
              <li key={item.key}>
                <Link
                  href={{ pathname: `/${slug}/shop`, query: { category: item.key } }}
                  className={chip(category === item.key)}
                  aria-current={category === item.key ? "page" : undefined}
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}

      {page.products.length === 0 ? (
        <EmptyState
          icon={<ShoppingBag size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3">
          {page.products.map((product) => (
            <li key={product.id}>
              <ProductCard product={product} shopSlug={slug} />
            </li>
          ))}
        </ul>
      )}

      {page.bundles.length > 0 && (
        <section aria-labelledby="bundles" className="flex flex-col gap-4">
          <h2 id="bundles" className="text-title flex items-center gap-2 font-bold">
            <Gift aria-hidden size={26} weight="duotone" className="text-hibiscus" />
            {t("bundles")}
          </h2>
          <ul className="flex flex-col gap-3">
            {page.bundles.map((bundle) => (
              <li
                key={bundle.id}
                className="border-trait rounded-card flex flex-col gap-3 border p-4"
              >
                <div className="flex flex-col gap-1">
                  <h3 className="text-lead font-bold">{bundle.title}</h3>
                  {bundle.description && <p className="text-prune-doux">{bundle.description}</p>}
                  <p className="text-small">
                    {bundle.items.map((item) => `${item.quantity} × ${item.title}`).join(", ")}
                  </p>
                </div>
                <p className="flex flex-wrap items-baseline gap-x-2">
                  <PriceTag amountMinor={bundle.price_minor} currency={bundle.currency} size="lg" />
                  {bundle.worth_minor > bundle.price_minor && (
                    <s className="text-prune-doux">
                      <span className="sr-only">{t("worth")} </span>
                      <PriceTag
                        amountMinor={bundle.worth_minor}
                        currency={bundle.currency}
                        className="font-normal"
                      />
                    </s>
                  )}
                </p>
                <BundleButton
                  bundleId={bundle.id}
                  disabled={bundle.stock < 1 || !page.delivery.is_open}
                  icon={<ShoppingBag aria-hidden size={22} weight="bold" />}
                />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="delivery" className="flex flex-col gap-4">
        <h2 id="delivery" className="text-title font-bold">
          {t("delivery")}
        </h2>
        <DeliveryInfo delivery={page.delivery} currency={currency} />
        {page.delivery.return_policy && (
          <p className="text-small text-prune-doux">{page.delivery.return_policy}</p>
        )}
      </section>
    </article>
  );
}
