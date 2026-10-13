import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { DemoOrder, SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

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

export default async function DemoPaymentPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <DemoOrder />
    </SignedIn>
  );
}
