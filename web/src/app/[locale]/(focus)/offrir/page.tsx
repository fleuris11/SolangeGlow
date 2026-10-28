import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import type { OfferStart } from "@/components/features/gifts/offer-flow";
import { OfferFlow } from "@/components/features/gifts/screens";
import { SignedIn } from "@/components/features/payments/screens";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "gifts.titles" });
  return { title: t("offer"), robots: { index: false, follow: false } };
}

const one = (value: string | string[] | undefined) =>
  typeof value === "string" ? value : undefined;

export default async function Page({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const query = await searchParams;
  const kind = one(query.kind);
  const start: OfferStart = {
    kind:
      kind === "card" || kind === "service" || kind === "product" || kind === "selection"
        ? kind
        : undefined,
    pro: one(query.pro),
    service: one(query.service),
    variant: one(query.variant),
    selection_product: one(query.selection_product),
    option: one(query.option),
  };
  return (
    <SignedIn>
      <OfferFlow start={start} />
    </SignedIn>
  );
}
