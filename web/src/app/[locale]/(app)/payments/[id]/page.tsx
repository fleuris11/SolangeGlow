import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { PaymentDetail, SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "payments.detail" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

type Props = { params: Promise<{ locale: Locale; id: string }> };

async function PaymentPage({ params }: Props) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  return (
    <SignedIn>
      <PaymentDetail paymentId={id} />
    </SignedIn>
  );
}

export default withClientMessages(PaymentPage, "[locale]/(app)/payments/[id]/page.tsx");
