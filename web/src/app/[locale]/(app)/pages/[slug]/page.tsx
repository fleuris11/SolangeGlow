import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getFormatter, getTranslations, setRequestLocale } from "next-intl/server";

import { RichText } from "@/components/features/help/rich-text";
import { SpeakButton } from "@/components/ui/speak-button";
import { pageOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = await pageOnServer(slug, locale).catch(() => null);
  return page ? { title: page.title, description: page.summary || undefined } : {};
}

/** A page written by the team in the admin: terms, privacy, legal notice, rules… */
export default async function ContentPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const page = await pageOnServer(slug, locale);
  if (!page) notFound();
  const t = await getTranslations({ locale, namespace: "help.page" });
  const format = await getFormatter({ locale });

  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-headline font-bold">{page.title}</h1>
          <SpeakButton text={page.title} className="mt-1" />
        </div>
        {page.summary && <p className="text-prune-doux">{page.summary}</p>}
        <p className="text-small text-prune-doux">
          {t("updated", {
            date: format.dateTime(new Date(page.updated_at), { dateStyle: "long" }),
          })}
        </p>
      </header>
      <RichText text={page.body} />
    </article>
  );
}
