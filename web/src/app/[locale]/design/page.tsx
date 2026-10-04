import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { Catalogue } from "@/components/features/design/catalogue";
import { HealthStatus } from "@/components/features/system/health-status";
import { BottomNav } from "@/components/ui/bottom-nav";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "design" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** Internal catalogue of the design system, in light and dark side by side. Not indexed. */
export default function DesignPage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("design");

  return (
    <main className="mx-auto flex max-w-[1400px] flex-col gap-8 px-4 py-10 pb-32">
      <header className="flex flex-col gap-2">
        <h1 className="font-display text-display font-black">{t("title")}</h1>
        <p className="text-prune-doux max-w-[60ch]">{t("intro")}</p>
      </header>
      <HealthStatus />
      <div className="grid min-w-0 grid-cols-1 gap-6 lg:grid-cols-2">
        {(["light", "dark"] as const).map((theme) => (
          <section
            key={theme}
            data-theme={theme}
            aria-labelledby={`panel-${theme}`}
            className="border-trait rounded-card min-w-0 border p-5"
          >
            <h2 id={`panel-${theme}`} className="text-title mb-6 font-bold">
              {t(`themes.${theme}`)}
            </h2>
            <Catalogue theme={theme} />
          </section>
        ))}
      </div>
      <BottomNav />
    </main>
  );
}
