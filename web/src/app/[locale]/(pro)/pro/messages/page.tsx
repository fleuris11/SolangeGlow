import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { MessagesHome } from "@/components/features/messaging/screens";
import { SpeakButton } from "@/components/ui/speak-button";
import { withClientMessages } from "@/lib/i18n/client-messages";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("messages") };
}

/** Her messages without leaving her professional space (its menu stays). */
function ProMessagesPage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("messages");
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-headline font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("help")}`} />
      </div>
      <MessagesHome visitor={null} />
    </div>
  );
}

export default withClientMessages(ProMessagesPage, "[locale]/(pro)/pro/messages/page.tsx");
