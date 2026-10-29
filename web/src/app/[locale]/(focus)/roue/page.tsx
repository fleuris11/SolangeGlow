import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { WheelScreen } from "@/components/features/games/screens";
import { SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "games.titles" });
  return { title: t("wheel"), robots: { index: false, follow: false } };
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <WheelScreen />
    </SignedIn>
  );
}
