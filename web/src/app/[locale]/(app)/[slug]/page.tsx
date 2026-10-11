import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { cache } from "react";

import { ShowcaseView } from "@/components/features/pros/showcase/showcase-view";
import { getShowcaseOnServer, SITE_URL } from "@/lib/api/server";
import { routing, type Locale } from "@/lib/i18n/routing";
import { mediaSrc } from "@/lib/media";
import { jsonLdScript, localBusinessJsonLd } from "@/lib/pros/json-ld";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

// Rendered on the server at each visit: always fresh, and readable by search engines.
export const dynamic = "force-dynamic";

/** One call per request, shared by the metadata and the page. */
const loadShowcase = cache((slug: string, locale: string) =>
  /^[a-z0-9-]{3,40}$/i.test(slug) ? getShowcaseOnServer(slug.toLowerCase(), locale) : null,
);

function absolute(url: string | undefined): string | undefined {
  if (!url) return undefined;
  return url.startsWith("http") ? url : `${SITE_URL}${url}`;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const showcase = await loadShowcase(slug, locale);
  if (!showcase) return {};
  const t = await getTranslations({ locale, namespace: "pros.showcase" });
  const tTrades = await getTranslations({ locale, namespace: "trades" });
  const trades = showcase.trades.map((trade) => tTrades(trade.key as "makeup")).join(", ");
  const description =
    showcase.bio.slice(0, 160) || t("metaDescription", { trades, city: showcase.place.city });
  const image = absolute(mediaSrc(showcase.photo, "large", "medium"));
  const canonical = `${SITE_URL}/${locale}/${showcase.slug}`;

  return {
    title: t("metaTitle", { name: showcase.business_name, trades, city: showcase.place.city }),
    description,
    alternates: {
      canonical,
      languages: Object.fromEntries(
        routing.locales.map((code) => [code, `${SITE_URL}/${code}/${showcase.slug}`]),
      ),
    },
    openGraph: {
      type: "profile",
      title: showcase.business_name,
      description,
      url: canonical,
      ...(image ? { images: [{ url: image }] } : {}),
    },
    twitter: { card: image ? "summary_large_image" : "summary" },
    robots: showcase.status === "published" ? undefined : { index: false, follow: false },
  };
}

export default async function ShowcasePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const showcase = await loadShowcase(slug, locale);
  if (!showcase) notFound();

  const url = `${SITE_URL}/${locale}/${showcase.slug}`;
  const jsonLd = localBusinessJsonLd(
    showcase,
    url,
    absolute(mediaSrc(showcase.photo, "large", "medium")),
  );

  return (
    <>
      <script
        type="application/ld+json"
        // Escaped by jsonLdScript: no "<" can close the script tag.
        dangerouslySetInnerHTML={{ __html: jsonLdScript(jsonLd) }}
      />
      <ShowcaseView showcase={showcase} />
    </>
  );
}
