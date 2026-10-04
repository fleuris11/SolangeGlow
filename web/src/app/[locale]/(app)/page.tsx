import Image from "next/image";
import { useTranslations } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use } from "react";

import { HealthStatus } from "@/components/features/system/health-status";
import { Link } from "@/lib/i18n/navigation";
import { routing, type Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export default function HomePage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations();

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col gap-8 px-4 py-12">
      <header className="flex flex-col items-start gap-4">
        <Image
          src="/icons/logo.png"
          alt={t("metadata.title")}
          width={200}
          height={98}
          priority
          className="rounded-2xl"
        />
        <h1 className="text-[30px] leading-9 font-bold">{t("home.tagline")}</h1>
        <p className="text-prune-doux">{t("home.underConstruction")}</p>
      </header>

      <HealthStatus />

      <nav aria-label={t("home.languages")}>
        <ul className="flex flex-wrap gap-2">
          {routing.locales.map((code) => (
            <li key={code}>
              <Link
                href="/"
                locale={code}
                hrefLang={code}
                aria-current={code === locale ? "true" : undefined}
                className="border-trait bg-poudre aria-[current=true]:border-hibiscus inline-flex min-h-12 items-center rounded-full border px-5"
              >
                {t(`locales.${code}`)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </main>
  );
}
