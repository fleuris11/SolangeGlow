import { UserCirclePlus } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { DisplaySettings } from "@/components/features/settings/display-settings";
import { Button } from "@/components/ui/button";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { Link } from "@/lib/i18n/navigation";
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
    <div className="flex flex-col gap-10">
      <h1 className="text-headline font-bold">{t("title")}</h1>

      <section
        aria-labelledby="guest-title"
        className="bg-poudre rounded-card flex flex-col items-start gap-3 p-5"
      >
        <UserCirclePlus aria-hidden size={40} weight="duotone" className="text-hibiscus" />
        <h2 id="guest-title" className="text-title font-bold">
          {t("guestTitle")}
        </h2>
        <p className="text-prune-doux">{t("guestText")}</p>
        <Button asChild size="lg">
          <Link href="/join">{t("cta")}</Link>
        </Button>
      </section>

      <DisplaySettings />

      <section aria-labelledby="language-title" className="flex flex-col gap-3">
        <h2 id="language-title" className="text-title font-bold">
          {t("language")}
        </h2>
        <LocaleSwitcher />
      </section>
    </div>
  );
}
