import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { cache } from "react";

import { ShopView } from "@/components/features/shop/shop-view";
import { SITE_URL, shopOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale; slug: string }>;
  searchParams: Promise<{ category?: string }>;
};

// Rendered on the server at each visit: prices and stock are always fresh.
export const dynamic = "force-dynamic";

const SLUG = /^[a-z0-9-]{3,40}$/i;
const loadShop = cache((slug: string, locale: string, category?: string) =>
  SLUG.test(slug) ? shopOnServer(slug.toLowerCase(), locale, category) : null,
);

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const { category } = await searchParams;
  const page = await loadShop(slug, locale, category);
  if (!page) return {};
  const t = await getTranslations({ locale, namespace: "shop.page" });
  return {
    title: t("title", { name: page.shop.name }),
    description: t("metaDescription", { name: page.shop.name, count: page.products.length }),
    alternates: { canonical: `${SITE_URL}/${locale}/${slug}/shop` },
  };
}

export default async function ShopPage({ params, searchParams }: Props) {
  const { locale, slug } = await params;
  const { category } = await searchParams;
  setRequestLocale(locale);
  const page = await loadShop(slug, locale, category);
  if (!page) notFound();
  return <ShopView page={page} slug={slug.toLowerCase()} category={category} />;
}
