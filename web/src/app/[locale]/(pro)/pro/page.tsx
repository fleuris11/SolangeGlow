import { Announcements } from "@/components/features/help/home-banner";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { SignedIn } from "@/components/features/payments/screens";
import { TodayScreen } from "@/components/features/pro-space/today";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ bienvenue?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "proSpace.today" });
  return { title: t("title"), robots: { index: false } };
}

async function Page({ params, searchParams }: Props) {
  const { locale } = await params;
  const { bienvenue } = await searchParams;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <Announcements placement="pro_space" locale={locale} />
      <TodayScreen welcome={bienvenue === "1"} />
    </SignedIn>
  );
}

export default withClientMessages(Page, "[locale]/(pro)/pro/page.tsx");
