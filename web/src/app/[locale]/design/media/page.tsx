import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { MediaTriage } from "@/components/features/design/media-triage";
import type { Locale } from "@/lib/i18n/routing";
import library from "@/lib/media/library.json";
import sources from "../../../../../scripts/media-sources.json";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "design.media" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

/** Internal page: the owner keeps or rejects the demonstration media. Not indexed. */
function MediaPage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("design.media");
  const media = library as Record<string, { src: string; poster?: string }>;
  const items = sources.map((item) => ({
    slug: item.slug,
    kind: item.kind,
    category: item.category,
    src: media[item.slug]?.src ?? "",
    poster: media[item.slug]?.poster,
    author: item.author,
    source: item.source,
    license: item.license,
    page: item.page ?? "",
  }));

  return (
    <main className="mx-auto flex max-w-[1400px] flex-col gap-6 px-4 py-10 pb-32">
      <header className="flex flex-col gap-2">
        <h1 className="font-display text-display font-black">{t("title")}</h1>
        <p className="text-prune-doux max-w-[60ch]">{t("intro")}</p>
      </header>
      <MediaTriage items={items} />
    </main>
  );
}

export default withClientMessages(MediaPage, "[locale]/design/media/page.tsx");
