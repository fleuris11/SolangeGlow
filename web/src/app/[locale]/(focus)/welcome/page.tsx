import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { WelcomeFlow } from "@/components/features/auth/welcome-flow";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ as?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "welcome" });
  return { title: t("metaTitle"), robots: { index: false } };
}

export default function WelcomePage({ params, searchParams }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const { as } = use(searchParams);
  return <WelcomeFlow as={as === "pro" || as === "client" ? as : undefined} />;
}
