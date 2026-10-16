import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { cache } from "react";

import { SelectionProductView } from "@/components/features/selection/selection-product";
import { SITE_URL, pickupPointsOnServer, selectionProductOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";
import { mediaSrc } from "@/lib/media";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamic = "force-dynamic";

const loadProduct = cache((slug: string, locale: string) =>
  /^[a-z0-9-]{1,160}$/i.test(slug) ? selectionProductOnServer(slug.toLowerCase(), locale) : null,
);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const product = await loadProduct(slug, locale);
  if (!product) return {};
  const t = await getTranslations({ locale, namespace: "selection.product" });
  const image = mediaSrc(product.photo, "large", "medium");
  return {
    title: t("metaTitle", { title: product.title }),
    description: product.description.slice(0, 160) || t("metaDescription"),
    alternates: { canonical: `${SITE_URL}/${locale}/selection/${product.slug}` },
    openGraph: {
      title: product.title,
      ...(image
        ? { images: [{ url: image.startsWith("http") ? image : `${SITE_URL}${image}` }] }
        : {}),
    },
  };
}

export default async function SelectionProductPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const [product, points] = await Promise.all([
    loadProduct(slug, locale),
    pickupPointsOnServer(locale),
  ]);
  if (!product) notFound();
  return <SelectionProductView product={product} points={points} />;
}
