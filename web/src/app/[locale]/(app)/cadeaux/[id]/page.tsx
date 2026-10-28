import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { SentGiftDetail } from "@/components/features/gifts/screens";
import { SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale; id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "gifts.titles" });
  return { title: t("detail"), robots: { index: false, follow: false } };
}

export default async function Page({ params, searchParams }: Props) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  const query = await searchParams;
  return (
    <SignedIn>
      <SentGiftDetail id={id} justPaid={query.paid === "1"} />
    </SignedIn>
  );
}
