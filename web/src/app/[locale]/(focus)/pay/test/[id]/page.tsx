import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { SignedIn, TestCheckout } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "payments.test" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

type Props = { params: Promise<{ locale: Locale; id: string }> };

export default async function TestPaymentPage({ params }: Props) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <TestCheckout paymentId={id} />
    </SignedIn>
  );
}
