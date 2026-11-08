import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { CalendarScreen } from "@/components/features/games/screens";

import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "games.titles" });
  return { title: t("calendar"), robots: { index: false, follow: false } };
}

async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <CalendarScreen />;
}

export default withClientMessages(Page, "[locale]/(app)/fetes/page.tsx");
