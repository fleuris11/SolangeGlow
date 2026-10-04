import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { MeContent } from "@/components/features/me/me-content";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("me") };
}

export default function MePage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("me");

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <MeContent />
    </div>
  );
}
