import {
  Crosshair,
  FadersHorizontal,
  ListBullets,
  MagnifyingGlass,
  MapTrifold,
} from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import dynamic from "next/dynamic";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Suspense } from "react";

import { ExploreControls } from "@/components/features/pros/explore/explore-controls";
import { paramsOf, readFilters, toApiQuery } from "@/components/features/pros/explore/filters";
import { LoadMore } from "@/components/features/pros/explore/load-more";
import { TradeNav } from "@/components/features/pros/explore/trade-nav";
import { ProCard } from "@/components/features/pros/pro-card";
import { SearchBar } from "@/components/features/search/search-bar";
import { buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SpeakButton } from "@/components/ui/speak-button";
import { placesOnServer, searchProsOnServer } from "@/lib/api/server";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";

// Map view only: its code (and MapLibre) is not part of the list page.
const ExploreMapView = dynamic(() =>
  import("@/components/features/pros/explore/explore-map-view").then((m) => m.ExploreMapView),
);

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "explore" });
  return { title: t("title"), description: t("metaDescription") };
}

/**
 * Explore: the first results are rendered on the server (readable before any script,
 * light on a 3G phone); near me, filters, map and « see more » are small islands.
 */
export default async function ExplorePage({ params, searchParams }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "explore" });
  const filters = readFilters(paramsOf(await searchParams));
  const query = toApiQuery(filters);
  const isMap = filters.view === "map";
  const results = isMap ? null : await searchProsOnServer(query, locale);
  const country = isMap
    ? (await placesOnServer(locale)).find((place) => place.city === filters.city)?.country
    : undefined;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-headline font-bold">{t("title")}</h1>
        <SpeakButton text={t("intro")} />
      </div>
      <SearchBar key={filters.q} defaultValue={filters.q} />
      <TradeNav filters={filters} />
      <Suspense>
        <ExploreControls
          icons={{
            near: <Crosshair aria-hidden size={22} weight="bold" />,
            filters: <FadersHorizontal aria-hidden size={22} weight="bold" />,
            map: <MapTrifold aria-hidden size={22} weight="bold" />,
            list: <ListBullets aria-hidden size={22} weight="bold" />,
          }}
        />
      </Suspense>

      {isMap ? (
        <ExploreMapView
          query={query}
          country={country}
          center={
            filters.lat !== undefined && filters.lng !== undefined
              ? [filters.lng, filters.lat]
              : undefined
          }
        />
      ) : results && results.results.length > 0 ? (
        <section aria-labelledby="results-title" className="flex flex-col gap-3">
          <h2 id="results-title" className="text-lead font-bold">
            {t("results", { count: results.count })}
          </h2>
          <ul className="flex flex-col gap-3">
            {results.results.map((pro) => (
              <li key={pro.slug}>
                <ProCard pro={pro} />
              </li>
            ))}
          </ul>
          <LoadMore key={JSON.stringify(query)} query={query} next={results.next ?? null} />
        </section>
      ) : (
        <EmptyState
          icon={<MagnifyingGlass size={48} weight="duotone" />}
          title={t("noResultTitle")}
          description={t("noResultText")}
          action={
            <Link href="/explore" className={buttonClasses({ variant: "secondary" })}>
              {t("clear")}
            </Link>
          }
        />
      )}
    </div>
  );
}
