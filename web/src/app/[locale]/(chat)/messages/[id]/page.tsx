import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { ThreadScreen } from "@/components/features/messaging/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale; id: string }>;
  searchParams: Promise<{ share?: string; slot?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("messages"), robots: { index: false, follow: false } };
}

export default async function ConversationPage({ params, searchParams }: Props) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  const { share, slot } = await searchParams;
  return <ThreadScreen conversationId={id} share={share} slot={slot} />;
}
