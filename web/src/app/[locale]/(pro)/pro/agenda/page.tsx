import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AgendaScreen } from "@/components/features/booking/screens";
import { SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ day?: string; rdv?: string }>;
};

const DAY = /^\d{4}-\d{2}-\d{2}$/;
const UUID = /^[0-9a-f-]{36}$/;

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "booking.titles" });
  return { title: t("agenda"), robots: { index: false, follow: false } };
}

export default async function Page({ params, searchParams }: Props) {
  const { locale } = await params;
  const { day, rdv } = await searchParams;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <AgendaScreen
        initialDay={day && DAY.test(day) ? day : undefined}
        initialAppointment={rdv && UUID.test(rdv) ? rdv : undefined}
      />
    </SignedIn>
  );
}
