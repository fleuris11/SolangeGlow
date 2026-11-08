import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { SignedIn } from "@/components/features/payments/screens";
import { LivesScreen } from "@/components/features/pro-space/lives";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "proSpace.lives" });
  return { title: t("title"), robots: { index: false } };
}

async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <LivesScreen />
    </SignedIn>
  );
}

export default withClientMessages(Page, "[locale]/(pro)/pro/lives/page.tsx");
