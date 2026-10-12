import type { Metadata } from "next";
import dynamic from "next/dynamic";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { SpeakButton } from "@/components/ui/speak-button";
import type { Locale } from "@/lib/i18n/routing";

const MyPosts = dynamic(() =>
  import("@/components/features/social/my-posts").then((m) => m.MyPosts),
);

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "social.myPosts" });
  return { title: t("title"), robots: { index: false } };
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "social.myPosts" });
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline font-bold">{t("title")}</h1>
          <p className="text-prune-doux">{t("help")}</p>
        </div>
        <SpeakButton text={`${t("title")}. ${t("help")}`} />
      </div>
      <MyPosts />
    </div>
  );
}
