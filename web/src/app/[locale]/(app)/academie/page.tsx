import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { CatalogueView, type CatalogueFilters } from "@/components/features/academy/catalogue-view";
import { Announcements } from "@/components/features/help/home-banner";
import { catalogueOnServer, tradesOnServer, type CatalogueQuery } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";
import { alternatesFor } from "@/lib/seo/alternates";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<Record<string, string | undefined>>;
};

// Rendered on the server: the catalogue is visible before any script.
export const dynamic = "force-dynamic";

const LEVELS = ["beginner", "intermediate", "expert"];
const LANGUAGES = ["fr", "en", "sk"];
const PRICINGS = ["free", "paid", "pass"];
const pick = (value: string | undefined, allowed: string[]) =>
  value && allowed.includes(value) ? value : undefined;

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "academy.catalogue" });
  return {
    title: t("title"),
    description: t("intro"),
    alternates: alternatesFor(locale, "/academie"),
  };
}

async function AcademyPage({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const raw = await searchParams;
  const filters: CatalogueFilters = {
    q: raw.q?.slice(0, 80) || undefined,
    trade: raw.trade?.slice(0, 40) || undefined,
    level: pick(raw.level, LEVELS),
    language: pick(raw.language, LANGUAGES),
    pricing: pick(raw.pricing, PRICINGS),
  };
  const query = { ...filters, cursor: raw.cursor || undefined } as CatalogueQuery;
  const [page, trades] = await Promise.all([
    catalogueOnServer(query, locale),
    tradesOnServer(locale),
  ]);
  return (
    <div className="flex flex-col gap-6">
      <Announcements placement="academy" locale={locale} />
      <CatalogueView page={page} trades={trades} filters={filters} />
    </div>
  );
}

export default withClientMessages(AcademyPage, "[locale]/(app)/academie/page.tsx");
