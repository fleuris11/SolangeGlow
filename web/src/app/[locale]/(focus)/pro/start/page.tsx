import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { BecomeProFlow } from "@/components/features/pros/become/become-pro-flow";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ invite?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pros.become" });
  return { title: t("title"), robots: { index: false } };
}

export default function BecomeProPage({ params, searchParams }: Props) {
  const { locale } = use(params);
  const { invite } = use(searchParams);
  setRequestLocale(locale);
  return <BecomeProFlow invite={typeof invite === "string" ? invite : undefined} />;
}
