import { ChatsCircle, Compass } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("messages") };
}

export default function MessagesPage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("messages");

  return (
    <>
      <h1 className="sr-only">{t("title")}</h1>
      <EmptyState
        icon={<ChatsCircle size={48} weight="duotone" />}
        title={t("emptyTitle")}
        description={t("emptyText")}
        action={
          <Button asChild size="lg">
            <Link href="/explore">
              <Compass aria-hidden size={24} weight="bold" />
              {t("cta")}
            </Link>
          </Button>
        }
      />
    </>
  );
}
