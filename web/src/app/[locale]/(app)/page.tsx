import { useTranslations } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use } from "react";

import { AvailableToday } from "@/components/features/home/available-today";
import { FranceSelectionBand, GiftBand, JoinBand } from "@/components/features/home/bands";
import { LooksFeed } from "@/components/features/home/looks-feed";
import { SearchBar } from "@/components/features/search/search-bar";
import { TradePetals } from "@/components/features/trades/trade-petals";
import { SpeakButton } from "@/components/ui/speak-button";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export default function HomePage({ params }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("home");

  return (
    <div className="flex flex-col gap-12">
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

      <AvailableToday />
      <LooksFeed />
      <FranceSelectionBand />
      <GiftBand />
      <JoinBand />
    </div>
  );
}
