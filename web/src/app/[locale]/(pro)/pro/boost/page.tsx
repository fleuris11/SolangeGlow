import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { BoostScreen } from "@/components/features/ads/screens";
import { SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ paid?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "ads.boost" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

export default async function Page({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const { paid } = await searchParams;
  return (
    <SignedIn>
      <BoostScreen justPaid={paid === "1"} />
    </SignedIn>
  );
}
