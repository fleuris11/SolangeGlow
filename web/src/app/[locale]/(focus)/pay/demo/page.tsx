import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { DemoOrder, SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "payments.demo" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

type Props = { params: Promise<{ locale: Locale }> };

async function DemoPaymentPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <DemoOrder />
    </SignedIn>
  );
}

export default withClientMessages(DemoPaymentPage, "[locale]/(focus)/pay/demo/page.tsx");
