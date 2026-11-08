import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { MarketingPage, TITLE } from "@/components/features/marketing/chrome";
import { CityPicker } from "@/components/shell/city-picker";
import { EditorialSection } from "@/components/ui/editorial-section";

import { ActivityPlate } from "./activity-plate";
import { AddressBlank } from "./address-blank";
import { Hero } from "./hero";
import "./home.css";
import { ProFree } from "./pro-free";
import { Services } from "./services";
import { QuestionIndex } from "./question-index";
import { Steps } from "./steps";
import { EverySkin } from "./every-skin";
import { TradeTiles } from "./trade-tiles";
import { TwoSides } from "./two-sides";

/** Home of a visitor: the product at work, the two sides of an account, then the real feed. */
export function PublicHome({ feed }: { feed: ReactNode }) {
  const t = useTranslations("home.public.feed");
  return (
    <MarketingPage>
      <Hero />
      <Services />
      <TwoSides />
      <EverySkin />
      <Steps />
      <ProFree />
      <TradeTiles />
      <ActivityPlate />
      <QuestionIndex />
      <AddressBlank />
      <EditorialSection
        aria-labelledby="feed-title"
        className="px-4 py-16 md:px-8 xl:px-10 xl:py-24"
      >
        <div className="mx-auto flex max-w-[40rem] flex-col gap-8">
          <div className="flex flex-col items-start gap-3">
            <h2 id="feed-title" className={`${TITLE} text-headline xl:text-display scroll-mt-4`}>
              {t("title")}
            </h2>
            <CityPicker />
          </div>
          {feed}
        </div>
      </EditorialSection>
    </MarketingPage>
  );
}
