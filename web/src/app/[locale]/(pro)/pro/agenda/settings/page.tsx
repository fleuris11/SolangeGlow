import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AgendaSettingsScreen } from "@/components/features/booking/screens";
import { SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "booking.titles" });
  return { title: t("agendaSettings"), robots: { index: false, follow: false } };
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <AgendaSettingsScreen />
    </SignedIn>
  );
}
