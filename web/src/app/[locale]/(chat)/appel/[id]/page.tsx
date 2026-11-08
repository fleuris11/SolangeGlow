import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { CallScreen } from "@/components/features/calls/screens";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = { params: Promise<{ locale: Locale; id: string }> };

const UUID = /^[0-9a-f-]{36}$/i;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "calls" });
  return { title: t("pageTitle"), robots: { index: false, follow: false } };
}

async function CallPage({ params }: Props) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  if (!UUID.test(id)) notFound();
  return <CallScreen callId={id} />;
}

export default withClientMessages(CallPage, "[locale]/(chat)/appel/[id]/page.tsx");
