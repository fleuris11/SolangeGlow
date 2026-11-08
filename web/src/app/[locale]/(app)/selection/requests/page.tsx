import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { SignedIn } from "@/components/features/payments/screens";
import { SpecialRequests } from "@/components/features/selection/screens";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "selection.titles" });
  return { title: t("requests"), robots: { index: false, follow: false } };
}

async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <SpecialRequests />
    </SignedIn>
  );
}

export default withClientMessages(Page, "[locale]/(app)/selection/requests/page.tsx");
