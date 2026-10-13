import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { PaymentList, SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "payments.list" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ role?: string }>;
};

export default async function PaymentsPage({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const { role } = await searchParams;
  const t = await getTranslations({ locale, namespace: "payments.list" });
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <SignedIn>
        <PaymentList initialRole={role === "seller" ? "seller" : "buyer"} />
      </SignedIn>
    </div>
  );
}
