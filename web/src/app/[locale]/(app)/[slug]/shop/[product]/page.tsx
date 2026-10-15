import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { cache } from "react";

import { ProductView } from "@/components/features/shop/product-view";
import { SITE_URL, productOnServer, productReviewsOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";
import { mediaSrc } from "@/lib/media";
import { jsonLdScript } from "@/lib/pros/json-ld";
import { productJsonLd } from "@/lib/shop/json-ld";

type Props = { params: Promise<{ locale: Locale; slug: string; product: string }> };

export const dynamic = "force-dynamic";

const SLUG = /^[a-z0-9-]{1,140}$/i;
const loadProduct = cache((slug: string, product: string, locale: string) =>
  SLUG.test(slug) && SLUG.test(product)
    ? productOnServer(slug.toLowerCase(), product.toLowerCase(), locale)
    : null,
);

function absolute(url: string | undefined): string | undefined {
  if (!url) return undefined;
  return url.startsWith("http") ? url : `${SITE_URL}${url}`;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug, product: productSlug } = await params;
  const product = await loadProduct(slug, productSlug, locale);
  if (!product) return {};
  const t = await getTranslations({ locale, namespace: "shop.product" });
  const image = absolute(mediaSrc(product.photo, "large", "medium"));
  const description =
    product.description.slice(0, 160) || t("metaDescription", { name: product.shop.name });
  return {
    title: t("metaTitle", { title: product.title, name: product.shop.name }),
    description,
    alternates: { canonical: `${SITE_URL}/${locale}${product.link}` },
    openGraph: {
      title: product.title,
      description,
      url: `${SITE_URL}/${locale}${product.link}`,
      ...(image ? { images: [{ url: image }] } : {}),
    },
    twitter: { card: image ? "summary_large_image" : "summary" },
  };
}

export default async function ProductPage({ params }: Props) {
  const { locale, slug, product: productSlug } = await params;
  setRequestLocale(locale);
  const product = await loadProduct(slug, productSlug, locale);
  if (!product) notFound();
  const reviews = await productReviewsOnServer(product.id, locale);
  const images = product.photos
    .map((photo) => absolute(mediaSrc(photo, "large", "medium")))
    .filter((url): url is string => Boolean(url));
  const jsonLd = productJsonLd(product, `${SITE_URL}/${locale}${product.link}`, images);
  return (
    <>
      <script
        type="application/ld+json"
        // Escaped by jsonLdScript: no "<" can close the script tag.
        dangerouslySetInnerHTML={{ __html: jsonLdScript(jsonLd) }}
      />
      <ProductView product={product} reviews={reviews} />
    </>
  );
}
