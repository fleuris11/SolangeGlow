import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AdSlot } from "@/components/features/ads/ad-cards";
import { SelectionHome } from "@/components/features/selection/selection-home";
import type { Schemas } from "@/lib/api/client";
import { SITE_URL, adsOnServer, selectionOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ aisle?: string }>;
};

// Rendered on the server: prices and availability are always fresh.
export const dynamic = "force-dynamic";

const AISLES = ["small_prices", "trending", "luxury"] as const;
type Aisle = Schemas["AisleEnum"];
const asAisle = (value?: string): Aisle | undefined =>
  (AISLES as readonly string[]).includes(value ?? "") ? (value as Aisle) : undefined;

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "selection.home" });
  return {
    title: t("title"),
    description: t("intro"),
    alternates: { canonical: `${SITE_URL}/${locale}/selection` },
  };
}

export default async function SelectionPage({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const aisle = asAisle((await searchParams).aisle);
  const [page, sponsored] = await Promise.all([
    selectionOnServer(locale, aisle),
    adsOnServer(locale, { placement: "product" }).catch(() => null),
  ]);
  return <SelectionHome page={page} aisle={aisle} sponsored={<AdSlot list={sponsored} />} />;
}
