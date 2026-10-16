import { cookies } from "next/headers";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { FranceSelectionBand, GiftBand, JoinBand } from "@/components/features/home/bands";
import { SearchBar } from "@/components/features/search/search-bar";
import { FeedSection } from "@/components/features/social/feed-section";
import { StoryStrip } from "@/components/features/social/story-strip";
import { TradePetals } from "@/components/features/trades/trade-petals";
import { SpeakButton } from "@/components/ui/speak-button";
import { feedOnServer, selectionOnServer, storiesOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

/**
 * Home: today's stories and the personalised feed (rendered on the server, visible before
 * any script). Visitors also get the search and the presentation bands.
 */
export default async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "home" });
  const tFeed = await getTranslations({ locale, namespace: "social.feed" });
  const signedIn = (await cookies()).get("sg_signed_in")?.value === "1";
  const [stories, feed, selection] = await Promise.all([
    storiesOnServer(locale),
    feedOnServer(locale),
    selectionOnServer(locale).catch(() => null),
  ]);
  // One product per aisle for the France Selection band.
  const picks = ["small_prices", "trending", "luxury"]
    .map((aisle) => selection?.results.find((product) => product.aisle === aisle))
    .filter((product) => product !== undefined);

  return (
    <div className="flex flex-col gap-10">
      {signedIn ? (
        <h1 className="sr-only">{t("question")}</h1>
      ) : (
        <section aria-labelledby="home-title" className="flex flex-col gap-6">
          <div className="flex items-start justify-between gap-3">
            <h1 id="home-title" className="font-display text-display lg:text-hero font-black">
              {t("question")}
            </h1>
            <SpeakButton text={t("question")} className="mt-1" />
          </div>
          <SearchBar />
          <TradePetals />
        </section>
      )}

      <StoryStrip groups={stories} />
      <FeedSection
        posts={feed.results}
        next={feed.next ?? null}
        title={signedIn ? tFeed("titleSignedIn") : tFeed("title")}
      />

      <FranceSelectionBand products={picks} />
      {!signedIn && (
        <>
          <GiftBand />
          <JoinBand />
        </>
      )}
    </div>
  );
}
