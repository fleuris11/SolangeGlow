import type { Metadata } from "next";
import { cookies } from "next/headers";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { HowItWorksPage } from "@/components/features/marketing/how-it-works";
import type { Locale } from "@/lib/i18n/routing";
import { alternatesFor } from "@/lib/seo/alternates";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "marketing.how" });
  return {
    title: t("title"),
    description: t("line"),
    alternates: alternatesFor(locale, "/comment-ca-marche"),
  };
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <HowItWorksPage signedIn={(await cookies()).get("sg_signed_in")?.value === "1"} />;
}
