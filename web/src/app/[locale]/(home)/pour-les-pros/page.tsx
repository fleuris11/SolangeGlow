import type { Metadata } from "next";
import { cookies } from "next/headers";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { ForProsPage } from "@/components/features/marketing/for-pros";
import type { Locale } from "@/lib/i18n/routing";
import { alternatesFor } from "@/lib/seo/alternates";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "marketing.pros" });
  return {
    title: t("metaTitle"),
    description: t("line"),
    alternates: alternatesFor(locale, "/pour-les-pros"),
  };
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <ForProsPage signedIn={(await cookies()).get("sg_signed_in")?.value === "1"} />;
}
