import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { OffersView } from "@/components/features/glowpro/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

const SLUG = /^[a-z0-9-]{3,40}$/i;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "glowpro.titles" });
  return { title: t("offers") };
}

export default async function Page({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  if (!SLUG.test(slug)) notFound();
  const t = await getTranslations({ locale, namespace: "glowpro.offers" });
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <OffersView slug={slug.toLowerCase()} />
    </div>
  );
}
