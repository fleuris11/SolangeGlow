import { ChatsCircle, SignIn } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { MessagesHome } from "@/components/features/messaging/screens";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("messages") };
}

/** Static page: the list arrives on the phone for signed-in people only. */
export default function MessagesPage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("messages");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-headline font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("help")}`} />
      </div>
      <MessagesHome
        visitor={
          <EmptyState
            icon={<ChatsCircle size={48} weight="duotone" />}
            title={t("visitorTitle")}
            description={t("visitorText")}
            action={
              <Button asChild size="lg">
                <Link href="/auth">
                  <SignIn aria-hidden size={24} weight="bold" />
                  {t("visitorCta")}
                </Link>
              </Button>
            }
          />
        }
      />
    </div>
  );
}
