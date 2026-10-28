import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { LiveRoom } from "@/components/features/live/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; kind: string; id: string }> };

const UUID = /^[0-9a-f-]{36}$/i;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "live" });
  return { title: t("pageTitle"), robots: { index: false, follow: false } };
}

/** A live (training or sale): on air, waiting, or its replay. */
export default async function LivePage({ params }: Props) {
  const { locale, kind, id } = await params;
  setRequestLocale(locale);
  if ((kind !== "training" && kind !== "sale") || !UUID.test(id)) notFound();
  return <LiveRoom kind={kind} id={id} />;
}
