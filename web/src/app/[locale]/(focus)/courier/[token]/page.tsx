import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { CourierConfirm } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "payments.courier" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

type Props = { params: Promise<{ locale: Locale; token: string }> };

/** For the courier: no account needed. */
async function CourierPage({ params }: Props) {
  const { locale, token } = await params;
  setRequestLocale(locale);
  return <CourierConfirm token={decodeURIComponent(token)} />;
}

export default withClientMessages(CourierPage, "[locale]/(focus)/courier/[token]/page.tsx");
