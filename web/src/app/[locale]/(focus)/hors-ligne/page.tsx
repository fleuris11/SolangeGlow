import { ArrowClockwise, GraduationCap, WifiSlash } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { buttonClasses } from "@/components/ui/button";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "offline" });
  return { title: t("title"), robots: { index: false } };
}

/**
 * Shown by the service worker when the network is gone and the page was never seen.
 * No script needed: « Try again » reloads the address that was asked.
 */
export default async function OfflinePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "offline" });
  return (
    <section className="flex flex-col items-center gap-5 py-10 text-center">
      <span
        aria-hidden
        className="bg-poudre text-hibiscus petal inline-flex size-24 items-center justify-center"
      >
        <WifiSlash size={48} />
      </span>
      <div className="flex items-start gap-2">
        <h1 className="font-display text-headline font-black">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("text")}`} className="mt-1" />
      </div>
      <p className="text-prune-doux max-w-[32ch]">{t("text")}</p>
      <a href="" className={buttonClasses({ size: "lg", fullWidth: true })}>
        <ArrowClockwise aria-hidden size={22} weight="bold" />
        {t("retry")}
      </a>
      <Link
        href="/academie/mes-formations"
        className={buttonClasses({ variant: "secondary", fullWidth: true })}
      >
        <GraduationCap aria-hidden size={22} />
        {t("lessons")}
      </Link>
    </section>
  );
}
