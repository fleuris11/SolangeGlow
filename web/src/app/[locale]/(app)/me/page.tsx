import { FileText, Lifebuoy } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { MeContent } from "@/components/features/me/me-content";
import { pagesOnServer } from "@/lib/api/server";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("me") };
}

const rowClass =
  "border-trait rounded-card bg-carte flex min-h-14 items-center gap-3 border px-4 py-3 font-bold";

export default async function MePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "me" });
  const pages = await pagesOnServer(locale).catch(() => []);

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <MeContent />
      <nav aria-labelledby="me-help" className="flex flex-col gap-2">
        <h2 id="me-help" className="text-title font-bold">
          {t("helpTitle")}
        </h2>
        <Link href="/aide" className={rowClass}>
          <Lifebuoy aria-hidden size={24} weight="duotone" className="text-hibiscus" />
          {t("help")}
        </Link>
        {pages
          .filter((page) => page.kind !== "help")
          .map((page) => (
            <Link key={page.slug} href={`/pages/${page.slug}`} className={rowClass}>
              <FileText aria-hidden size={24} weight="duotone" className="text-prune-doux" />
              {page.title}
            </Link>
          ))}
      </nav>
    </div>
  );
}
