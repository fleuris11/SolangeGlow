import { House, Sparkle } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ as?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "join" });
  return { title: t("title") };
}

/** Sign-up arrives with the accounts step: this page says so honestly. */
export default function JoinPage({ params, searchParams }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const { as } = use(searchParams);
  const t = useTranslations("join");

  return (
    <>
      <h1 className="sr-only">{t("title")}</h1>
      <EmptyState
        icon={<Sparkle size={48} weight="duotone" />}
        title={t("soonTitle")}
        description={as === "pro" ? t("soonPro") : t("soonClient")}
        action={
          <Button asChild variant="secondary" size="lg">
            <Link href="/">
              <House aria-hidden size={24} weight="bold" />
              {t("home")}
            </Link>
          </Button>
        }
      />
    </>
  );
}
