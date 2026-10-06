import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { NotificationsContent } from "@/components/features/notifications/notifications-content";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "notifications" });
  return { title: t("title"), robots: { index: false } };
}

export default function NotificationsPage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("notifications");

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <NotificationsContent />
    </div>
  );
}
