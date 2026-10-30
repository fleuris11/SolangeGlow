import {
  CaretDown,
  Lifebuoy,
  MagnifyingGlass,
  PaperPlaneTilt,
} from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { HelpContact } from "@/components/features/help/help-contact";
import { RichText } from "@/components/features/help/rich-text";
import { SpeakButton } from "@/components/ui/speak-button";
import { faqOnServer, pagesOnServer } from "@/lib/api/server";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "help" });
  return { title: t("title") };
}

/** Help center: ask a question (answers of the FAQ first), then the FAQ by topic. */
export default async function HelpPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "help" });
  const [topics, pages] = await Promise.all([
    faqOnServer(locale).catch(() => []),
    pagesOnServer(locale).catch(() => []),
  ]);

  return (
    <div className="flex flex-col gap-10">
      <header className="flex items-start justify-between gap-3">
        <h1 className="text-headline flex items-center gap-3 font-bold">
          <Lifebuoy aria-hidden size={32} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} className="mt-1" />
      </header>

      <HelpContact
        searchIcon={<MagnifyingGlass aria-hidden size={20} />}
        sendIcon={<PaperPlaneTilt aria-hidden size={20} />}
      />

      {topics.length > 0 && (
        <section aria-labelledby="faq-title" className="flex flex-col gap-6">
          <h2 id="faq-title" className="text-title font-bold">
            {t("faq")}
          </h2>
          {topics.map((topic) => (
            <div key={topic.key} className="flex flex-col gap-2">
              <h3 className="text-lead font-bold">{topic.label}</h3>
              {topic.items.map((item) => (
                <details
                  key={item.id}
                  className="border-trait rounded-card bg-carte group border px-4"
                >
                  <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 py-3 font-bold">
                    {item.question}
                    <CaretDown
                      aria-hidden
                      size={20}
                      className="shrink-0 transition-transform duration-150 group-open:rotate-180"
                    />
                  </summary>
                  <div className="pb-4">
                    <RichText text={item.answer} />
                  </div>
                </details>
              ))}
            </div>
          ))}
        </section>
      )}

      {pages.length > 0 && (
        <nav aria-labelledby="pages-title" className="flex flex-col gap-2">
          <h2 id="pages-title" className="text-title font-bold">
            {t("pages")}
          </h2>
          <ul className="flex flex-col gap-1">
            {pages.map((page) => (
              <li key={page.slug}>
                <Link
                  href={`/pages/${page.slug}`}
                  className="text-hibiscus inline-flex min-h-12 items-center font-bold underline-offset-4 hover:underline"
                >
                  {page.title}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  );
}
