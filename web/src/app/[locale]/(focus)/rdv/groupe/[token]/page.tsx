import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { GroupView } from "@/components/features/booking/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; token: string }> };

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "booking.titles" });
  return { title: t("group"), robots: { index: false, follow: false } };
}

export default async function Page({ params }: Props) {
  const { locale, token } = await params;
  setRequestLocale(locale);
  return <GroupView token={token} />;
}
