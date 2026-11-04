import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { MyShowcase } from "@/components/features/pros/my/my-showcase";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pros.my" });
  return { title: t("title"), robots: { index: false } };
}

export default function MyShowcasePage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  return <MyShowcase />;
}
