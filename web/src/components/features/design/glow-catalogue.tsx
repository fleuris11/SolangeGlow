"use client";

import { Sparkle } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { TRADES } from "@/components/features/trades/trade-icon";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { BeforeAfterSlider } from "@/components/ui/before-after-slider";
import { Bloom } from "@/components/ui/bloom";
import { BottomSheet } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { ImageGallery } from "@/components/ui/image-gallery";
import { LikeBurst } from "@/components/ui/like-burst";
import { Marquee } from "@/components/ui/marquee";
import { MediaHero } from "@/components/ui/media-hero";
import { ParallaxImage } from "@/components/ui/parallax-image";
import { PhotoCard } from "@/components/ui/photo-card";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { SharedElement } from "@/components/ui/shared-element";
import { SkeletonShape } from "@/components/ui/skeleton-shape";
import { StoryViewer } from "@/components/ui/story-viewer";
import { SwitchRow } from "@/components/ui/switch-row";
import library from "@/lib/media/library.json";
import { usePreferences } from "@/lib/preferences/preferences-provider";

const MEDIA = library as Record<string, { src: string; color?: string }>;
const photo = (slug: string) => MEDIA[slug]!.src;

function Sample({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-trait rounded-card flex min-w-0 flex-col gap-3 border p-4">
      <h3 className="text-lead font-bold">{title}</h3>
      {children}
    </section>
  );
}

/** The switch that applies to the whole page: every animation, with and without. */
export function MotionSwitch() {
  const t = useTranslations("design.glow");
  const { reducedMotion, update } = usePreferences();
  return (
    <SwitchRow
      icon={<Sparkle size={28} />}
      label={t("reduced")}
      description={t("reducedText")}
      checked={reducedMotion}
      onChange={(value) => update({ reducedMotion: value })}
    />
  );
}

/** The components of Glow v2 with demonstration photos. Rendered once per theme on /design. */
export function GlowCatalogue() {
  const t = useTranslations("design.glow");
  const tTrades = useTranslations("trades");
  const tAlt = useTranslations("home.public.alt");
  const [sheet, setSheet] = useState(false);
  const [stories, setStories] = useState(false);
  const [likes, setLikes] = useState(128);
  const [bloom, setBloom] = useState(0);

  return (
    <div className="flex flex-col gap-4">
      <Sample title="MediaHero">
        <MediaHero
          src={photo("hero-afro-profile")}
          alt={tAlt("hair")}
          reveal
          glow={MEDIA["hero-afro-profile"]!.color}
          sizes="400px"
          className="mx-auto aspect-[4/5] w-full max-w-[280px]"
        />
      </Sample>
      <Sample title="EditorialSection">
        <EditorialSection ambiance="nuit" className="rounded-card p-5">
          <p className="font-display text-title font-bold">{t("night")}</p>
          <Button className="mt-3">{t("action")}</Button>
        </EditorialSection>
      </Sample>
      <Sample title="PhotoCard">
        <PhotoCard
          src={photo("braids-hoops")}
          alt={tAlt("braids")}
          title={tTrades("braids")}
          subtitle="15 000 FCFA"
          glow={MEDIA["braids-hoops"]!.color}
          sizes="400px"
          className="max-w-[280px]"
        />
      </Sample>
      <Sample title="ParallaxImage">
        <ParallaxImage
          src={photo("bride-afro")}
          alt={tAlt("booking")}
          sizes="400px"
          className="rounded-photo h-56"
        />
      </Sample>
      <Sample title="BeforeAfterSlider">
        <BeforeAfterSlider
          before={photo("skin-profile")}
          after={photo("skin-warm")}
          beforeAlt={tAlt("skincare")}
          afterAlt={tAlt("skincare")}
          sizes="400px"
          className="max-w-[280px]"
        />
      </Sample>
      <Sample title="ImageGallery">
        <ImageGallery
          sizes="400px"
          className="rounded-photo max-w-[280px] overflow-hidden"
          images={[
            { src: photo("palette"), alt: "" },
            { src: photo("brushes"), alt: "" },
            { src: photo("nails-pro"), alt: "" },
          ]}
        />
      </Sample>
      <Sample title="StoryViewer">
        <Button variant="secondary" onClick={() => setStories(true)}>
          {t("openStories")}
        </Button>
        <StoryViewer
          open={stories}
          onOpenChange={setStories}
          title={t("openStories")}
          stories={[
            { id: "a", src: photo("hero-orange-hat"), alt: tAlt("headwrap"), caption: t("night") },
            { id: "b", src: photo("braids-yellow"), alt: tAlt("braids"), caption: t("action") },
          ]}
        />
      </Sample>
      <Sample title="SharedElement">
        <SharedElement name="design-sample">
          <p className="text-prune-doux text-small">{t("shared")}</p>
        </SharedElement>
      </Sample>
      <Sample title="LikeBurst, AnimatedNumber">
        <button
          type="button"
          onClick={() => setLikes((value) => value + 1)}
          className="press bg-poudre relative inline-flex min-h-12 w-fit items-center gap-2 rounded-full px-5 font-bold"
        >
          <LikeBurst key={likes} />
          {t("like")} <AnimatedNumber value={likes} />
        </button>
      </Sample>
      <Sample title="PullToRefresh">
        <PullToRefresh onRefresh={() => new Promise((done) => setTimeout(done, 800))}>
          <p className="text-prune-doux text-small">{t("pull")}</p>
        </PullToRefresh>
      </Sample>
      <Sample title="BottomSheet">
        <Button variant="secondary" onClick={() => setSheet(true)}>
          {t("openSheet")}
        </Button>
        <BottomSheet open={sheet} onOpenChange={setSheet} title={t("openSheet")}>
          <p>{t("sheetText")}</p>
        </BottomSheet>
      </Sample>
      <Sample title="Bloom v2">
        <Bloom key={bloom} label={t("bloom")} />
        <Button variant="quiet" className="w-fit" onClick={() => setBloom((value) => value + 1)}>
          {t("replay")}
        </Button>
      </Sample>
      <Sample title="Marquee">
        <Marquee label={t("trades")}>
          {TRADES.map((trade) => (
            <span key={trade} className="font-display text-headline font-bold">
              {tTrades(trade)}
            </span>
          ))}
        </Marquee>
      </Sample>
      <Sample title="SkeletonShape">
        <div className="grid grid-cols-2 gap-4">
          <SkeletonShape shape="post" />
          <SkeletonShape shape="product" />
          <SkeletonShape shape="pro" />
          <SkeletonShape shape="list" />
        </div>
      </Sample>
    </div>
  );
}
