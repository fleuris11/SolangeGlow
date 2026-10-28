import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { CallLog } from "@/components/features/calls/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "calls.log" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

export default async function CallLogPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <CallLog />;
}
