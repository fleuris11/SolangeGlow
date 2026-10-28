import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { GiftReception } from "@/components/features/gifts/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; token: string }> };

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "gifts.titles" });
  // A secret link: never in search engines, never sent to other sites.
  return { title: t("gift"), robots: { index: false, follow: false }, referrer: "no-referrer" };
}

export default async function Page({ params }: Props) {
  const { locale, token } = await params;
  setRequestLocale(locale);
  return <GiftReception token={token} />;
}
