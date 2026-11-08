import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Suspense } from "react";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AdSlot } from "@/components/features/ads/ad-cards";
import { SplashLoader } from "@/components/features/ads/splash-loader";
import { GlowTodayBand, WinnerBand } from "@/components/features/games/home-band";
import { HomeBanners } from "@/components/features/help/home-banner";
import { FranceSelectionBand } from "@/components/features/home/bands";
import { PublicHome } from "@/components/features/home/public-home";
import { UpcomingLivesBand } from "@/components/features/live/upcoming-band";
import { SearchBar } from "@/components/features/search/search-bar";
import { Skeleton } from "@/components/ui/skeleton";
import { FeedSection } from "@/components/features/social/feed-section";
import { StoryStrip } from "@/components/features/social/story-strip";
import { HomeInstallPrompt } from "@/components/pwa/home-install-prompt";
import { AppShell } from "@/components/shell/app-shell";
import {
  adsOnServer,
  feedOnServer,
  glowTodayOnServer,
  homeBannersOnServer,
  selectionOnServer,
  storiesOnServer,
  upcomingLivesOnServer,
} from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";
import { alternatesFor } from "@/lib/seo/alternates";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return { alternates: alternatesFor(locale, "/") };
}

/**
 * Home. A visitor gets the edge-to-edge public page, with the real feed further down; a signed-in
 * person gets her stories and her feed in the app shell. Rendered on the server either way.
 */
async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "home" });
  const signedIn = (await cookies()).get("sg_signed_in")?.value === "1";
  // Streamed: the top of the page leaves at once, the feed follows when its data is there.
  const feed = (
    <Suspense fallback={<Skeleton className="rounded-card h-96" />}>
      <HomeFeed locale={locale} signedIn={signedIn} />
    </Suspense>
  );

  if (!signedIn) {
    return (
      <PublicHome
        feed={
          <>
            <SearchBar />
            {feed}
          </>
        }
      />
    );
  }
  return (
    <AppShell>
      <h1 className="sr-only">{t("question")}</h1>
      {feed}
    </AppShell>
  );
}

/** Everything that needs the backend: stories, feed, lives, games, ads, Selection. */
async function HomeFeed({ locale, signedIn }: { locale: Locale; signedIn: boolean }) {
  const tFeed = await getTranslations({ locale, namespace: "social.feed" });
  const [stories, feed, selection, lives, glow, banner, sponsored, editorial] = await Promise.all([
    storiesOnServer(locale),
    feedOnServer(locale),
    selectionOnServer(locale).catch(() => null),
    upcomingLivesOnServer(locale).catch(() => []),
    glowTodayOnServer(locale).catch(() => null),
    adsOnServer(locale, { placement: "home_banner" }).catch(() => null),
    adsOnServer(locale, { placement: "feed", count: 2 }).catch(() => null),
    homeBannersOnServer(locale).catch(() => []),
  ]);
  // One product per aisle for the France Selection band.
  const picks = ["small_prices", "trending", "luxury"]
    .map((aisle) => selection?.results.find((product) => product.aisle === aisle))
    .filter((product) => product !== undefined);

  const content = (
    <div className="flex flex-col gap-10">
      <SplashLoader />
      <HomeBanners banners={editorial} />
      <HomeInstallPrompt />
      <AdSlot list={banner} />
      <StoryStrip groups={stories} />
      {glow && <GlowTodayBand today={glow} />}
      <UpcomingLivesBand lives={lives} />
      {glow && <WinnerBand featured={glow.featured} />}
      <FeedSection
        posts={feed.results}
        next={feed.next ?? null}
        title={signedIn ? tFeed("titleSignedIn") : tFeed("title")}
        sponsored={sponsored}
      />
      <FranceSelectionBand products={picks} />
    </div>
  );

  return content;
}

export default withClientMessages(HomePage, "[locale]/(home)/page.tsx");
