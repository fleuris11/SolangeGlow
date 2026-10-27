import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { MyAcademyScreen } from "@/components/features/academy/screens";
import { SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "academy.titles" });
  return { title: t("mine"), robots: { index: false, follow: false } };
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <MyAcademyScreen />
    </SignedIn>
  );
}
