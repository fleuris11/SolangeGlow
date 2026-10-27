import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { LiveRoomScreen } from "@/components/features/academy/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; id: string }> };

const UUID = /^[0-9a-f-]{36}$/i;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "academy.titles" });
  return { title: t("live"), robots: { index: false, follow: false } };
}

export default async function Page({ params }: Props) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  if (!UUID.test(id)) notFound();
  return <LiveRoomScreen liveId={id} />;
}
