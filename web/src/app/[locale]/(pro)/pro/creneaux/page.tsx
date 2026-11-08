import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { SignedIn } from "@/components/features/payments/screens";
import { AvailabilityScreen } from "@/components/features/pro-space/availability";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "proSpace.slots" });
  return { title: t("title"), robots: { index: false } };
}

async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <AvailabilityScreen />
    </SignedIn>
  );
}

export default withClientMessages(Page, "[locale]/(pro)/pro/creneaux/page.tsx");
