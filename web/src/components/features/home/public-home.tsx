import { useLocale, useTranslations } from "next-intl";
import Image from "next/image";
import type { ComponentProps, CSSProperties, ReactNode } from "react";

import { TradeIcon, TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { AudioToggle } from "@/components/shell/audio-toggle";
import { CityPicker } from "@/components/shell/city-picker";
import { navIcons } from "@/components/shell/nav-icons";
import { AutoplayVideo } from "@/components/ui/autoplay-video";
import { BottomNav } from "@/components/ui/bottom-nav";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { ParallaxImage } from "@/components/ui/parallax-image";
import { PhotoCard } from "@/components/ui/photo-card";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

type Photo = keyof typeof library;
const MEDIA = library as Record<string, { src: string; color?: string; poster?: string }>;

const TRADE_PHOTOS: Record<Trade, Photo> = {
  hair: "hero-afro-profile",
  braids: "braids-yellow",
  makeup: "makeup-portrait",
  nails: "nails-lips",
  sewing: "sewing",
  headwrap: "headwrap-smile",
  skincare: "skin-warm",
};
const FIRST_TRADE: Trade = "hair";
const ORDER: Trade[] = [FIRST_TRADE, ...TRADES.filter((trade) => trade !== FIRST_TRADE)];
const CODE = ["4", "8", "1", "7", "2", "6"];
const PLACES = "Cotonou, Calavi, Porto-Novo, Paris, Brest";

function src(photo: Photo) {
  return MEDIA[photo]!.src;
}

/** The name of the platform as architecture: decorative, the page title says it in words. */
function Monument({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={`font-display pointer-events-none leading-[0.82] font-black tracking-[-0.05em] whitespace-nowrap select-none ${className ?? ""}`}
    >
      Solange
    </div>
  );
}

function TopBar() {
  const t = useTranslations("home.public");
  return (
    <header className="relative z-20 flex items-center justify-end gap-3 px-4 py-1 lg:justify-between lg:px-10 lg:py-5">
      <Link
        href="/"
        className="font-display text-hibiscus lg:text-title hidden font-black whitespace-nowrap lg:block"
      >
        Solange glow
      </Link>
      <nav aria-label={t("menu")} className="hidden items-center gap-8 font-bold lg:flex">
        <Link href="/explore">{t("links.explore")}</Link>
        <Link href="/selection">{t("links.shop")}</Link>
        <Link href="/academie">{t("links.academy")}</Link>
        <Link href="/offrir">{t("links.gift")}</Link>
      </nav>
      <div className="flex items-center gap-1">
        <AudioToggle compact />
        <Button
          asChild
          variant="secondary"
          className="text-small min-h-11 px-3 whitespace-nowrap lg:px-5"
        >
          <Link href="/auth">{t("signIn")}</Link>
        </Button>
      </div>
    </header>
  );
}

/**
 * The opening. Choosing a trade changes the picture and the button with native radio buttons
 * and CSS only (globals.css, .sg-chooser): no script, keyboard included, and a picture that is
 * not shown is not downloaded.
 */
function Opening() {
  const t = useTranslations("home.public");
  const tTrades = useTranslations("trades");
  return (
    <EditorialSection
      ambiance="nuit"
      aria-labelledby="home-title"
      className="sg-chooser flex min-h-[calc(100svh-4rem)] flex-col overflow-x-clip overflow-y-clip lg:min-h-svh"
    >
      <TopBar />
      <div className="relative flex flex-1 flex-col px-4 lg:block lg:px-10">
        <div className="relative mx-auto aspect-[4/5] w-[82%] max-w-[300px] shrink-0 lg:absolute lg:top-0 lg:right-[10%] lg:h-[calc(100svh-7rem)] lg:w-auto lg:max-w-none">
          {ORDER.map((trade, index) => (
            <div
              key={trade}
              data-show={trade}
              className="absolute inset-0"
              style={{ "--lueur": MEDIA[TRADE_PHOTOS[trade]]!.color } as CSSProperties}
            >
              <span aria-hidden className="sg-glow" />
              <div className="sg-petal-reveal relative size-full overflow-hidden">
                <Image
                  src={src(TRADE_PHOTOS[trade])}
                  alt={t(`alt.${trade}`)}
                  fill
                  priority={index === 0}
                  loading={index === 0 ? undefined : "lazy"}
                  sizes="(min-width: 1024px) 45vw, 82vw"
                  className="object-cover"
                />
              </div>
            </div>
          ))}
        </div>

        <Monument className="sg-rise relative z-10 -mt-[12vw] text-center text-[29.5vw] lg:absolute lg:inset-x-0 lg:bottom-0 lg:mt-0 lg:text-[25.5vw]" />

        <div className="relative z-20 mt-3 flex flex-col gap-3 lg:mt-0 lg:max-w-[520px] lg:gap-6">
          <div className="sg-line-up flex items-start justify-between gap-2">
            <h1
              id="home-title"
              className="text-lead lg:font-display font-bold lg:text-[2.5rem] lg:leading-[1.1] lg:font-black"
            >
              {t("title")}
            </h1>
            <SpeakButton text={t("title")} />
          </div>

          <fieldset className="sg-line-up min-w-0 [--line:1]">
            <legend className="sr-only">{t("chooseTrade")}</legend>
            <ul className="-mx-4 flex [scrollbar-width:none] gap-2 overflow-x-auto px-4 lg:mx-0 lg:flex-col lg:gap-0 lg:overflow-visible lg:px-0">
              {ORDER.map((trade) => (
                <li key={trade} className="relative shrink-0">
                  <input
                    type="radio"
                    name="home-trade"
                    id={`trade-${trade}`}
                    value={trade}
                    defaultChecked={trade === FIRST_TRADE}
                    className="peer sr-only"
                  />
                  <label
                    htmlFor={`trade-${trade}`}
                    className="press bg-poudre peer-checked:bg-hibiscus peer-checked:text-sur-hibiscus peer-focus-visible:outline-hibiscus lg:peer-checked:text-hibiscus lg:font-display flex min-h-12 cursor-pointer items-center gap-2 rounded-full px-4 font-bold peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 lg:min-h-11 lg:bg-transparent lg:px-0 lg:text-[1.875rem] lg:leading-[1.2] lg:font-bold lg:peer-checked:bg-transparent"
                  >
                    <TradeIcon trade={trade} size={24} />
                    {tTrades(trade)}
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>

          <div className="sg-line-up [--line:2]">
            {ORDER.map((trade) => (
              <div key={trade} data-show={trade}>
                <Button asChild size="lg" className="w-full lg:w-auto">
                  <Link href={{ pathname: "/explore", query: { trade } }}>
                    {t(`find.${trade}`)}
                  </Link>
                </Button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </EditorialSection>
  );
}

function Print({
  photo,
  alt,
  title,
  text,
  trade,
  ...props
}: { photo: Photo; alt: string; title: string; text: string; trade: Trade } & Pick<
  ComponentProps<typeof PhotoCard>,
  "className" | "sizes"
>) {
  return (
    <Link
      href={{ pathname: "/explore", query: { trade } }}
      className={`press block ${props.className ?? ""}`}
    >
      <div className="rounded-photo relative aspect-[4/5] overflow-hidden">
        <Image src={src(photo)} alt={alt} fill sizes={props.sizes} className="object-cover" />
      </div>
      <h3 className="font-display text-title mt-3 font-bold">{title}</h3>
      <p className="text-prune-doux text-small">{text}</p>
    </Link>
  );
}

function Hands() {
  const t = useTranslations("home.public.hands");
  const alt = useTranslations("home.public.alt");
  return (
    <EditorialSection aria-labelledby="hands-title" className="px-4 py-16 lg:px-10 lg:py-28">
      <h2
        id="hands-title"
        className="font-display text-[2.5rem] leading-[1.05] font-black text-balance hyphens-none lg:max-w-[12ch] lg:text-[7.5rem] lg:leading-none"
      >
        {t("title")}
      </h2>
      <div className="mt-10 grid grid-cols-6 gap-x-4 gap-y-10 lg:mt-16 lg:grid-cols-12 lg:gap-x-8">
        <Print
          photo="braids-hoops"
          alt={alt("braids")}
          title={t("braids")}
          text={t("braidsText")}
          trade="braids"
          className="col-span-5 lg:col-span-4"
          sizes="(min-width: 1024px) 30vw, 80vw"
        />
        <Print
          photo="lips-orange"
          alt={alt("makeup")}
          title={t("makeup")}
          text={t("makeupText")}
          trade="makeup"
          className="col-span-5 col-start-2 lg:col-span-5 lg:col-start-5 lg:mt-24"
          sizes="(min-width: 1024px) 40vw, 80vw"
        />
        <Print
          photo="hero-orange-hat"
          alt={alt("headwrap")}
          title={t("headwrap")}
          text={t("headwrapText")}
          trade="headwrap"
          className="col-span-4 lg:col-span-3 lg:col-start-10 lg:-mt-40"
          sizes="(min-width: 1024px) 22vw, 60vw"
        />
      </div>
    </EditorialSection>
  );
}

function Booking() {
  const t = useTranslations("home.public.booking");
  const alt = useTranslations("home.public.alt");
  return (
    <EditorialSection
      ambiance="poudre"
      aria-labelledby="booking-title"
      className="grid lg:grid-cols-[1fr_55%]"
    >
      <div className="flex flex-col justify-center gap-6 px-4 py-16 lg:px-10">
        <h2
          id="booking-title"
          className="font-display text-[2.5rem] leading-[1.05] font-black text-balance hyphens-none lg:text-[4.5rem]"
        >
          {t("title")}
        </h2>
        <p className="text-lead max-w-[40ch]">{t("text")}</p>
        <div aria-hidden className="bg-carte rounded-card flex w-fit flex-col gap-3 p-5">
          <span className="font-bold">{t("day")}</span>
          <span className="flex flex-wrap gap-2 font-bold">
            <span className="bg-poudre rounded-full px-4 py-2">9 h</span>
            <span className="bg-hibiscus text-sur-hibiscus rounded-full px-4 py-2">10 h 30</span>
            <span className="bg-poudre rounded-full px-4 py-2">14 h</span>
          </span>
        </div>
        <Button asChild variant="secondary" className="w-fit">
          <Link href="/explore">{t("cta")}</Link>
        </Button>
      </div>
      <ParallaxImage
        src={src("bride-afro")}
        alt={alt("booking")}
        sizes="(min-width: 1024px) 55vw, 100vw"
        className="min-h-[420px] lg:min-h-[720px]"
      />
    </EditorialSection>
  );
}

/** What only this platform has: the money stays held until this code is given. */
function ReceiptCode() {
  const t = useTranslations("home.public.code");
  const steps = ["paid", "received", "given"] as const;
  return (
    <EditorialSection
      ambiance="nuit"
      aria-labelledby="code-title"
      className="px-4 py-16 lg:px-10 lg:py-28"
    >
      <div className="flex items-start justify-between gap-3">
        <h2
          id="code-title"
          className="font-display text-[2.5rem] leading-[1.05] font-black text-balance hyphens-none lg:max-w-[16ch] lg:text-[5.5rem]"
        >
          {t("title")}
        </h2>
        <SpeakButton text={t("title")} />
      </div>
      <p aria-hidden className="mt-8 grid grid-cols-6 gap-1.5 lg:mt-14 lg:gap-3">
        {CODE.map((digit, index) => (
          <span
            key={index}
            style={{ "--line": index } as CSSProperties}
            className="border-or text-or bg-carte font-display rounded-field lg:rounded-card sg-digit flex aspect-[3/4] items-center justify-center border-2 text-[2rem] font-black lg:text-[7.5rem]"
          >
            {digit}
          </span>
        ))}
      </p>
      <ol className="mt-8 flex flex-col gap-4 lg:mt-14 lg:grid lg:grid-cols-3 lg:gap-12">
        {steps.map((step) => (
          <li key={step}>
            <h3 className="text-title font-bold">{t(`${step}.title`)}</h3>
            <p className="text-prune-doux">{t(`${step}.text`)}</p>
          </li>
        ))}
      </ol>
    </EditorialSection>
  );
}

function ShopAndAcademy() {
  const t = useTranslations("home.public.more");
  return (
    <EditorialSection aria-labelledby="more-title" className="px-4 py-16 lg:px-10 lg:py-28">
      <h2 id="more-title" className="sr-only">
        {t("title")}
      </h2>
      <div className="grid gap-12 lg:grid-cols-12 lg:gap-8">
        <Link href="/selection" className="press block lg:col-span-7">
          <div className="rounded-photo relative aspect-[3/2] overflow-hidden">
            <AutoplayVideo
              src={MEDIA["video-table"]!.src}
              poster={MEDIA["video-table"]!.poster}
              className="absolute inset-0 z-10 size-full object-cover"
            />
            <Image
              src={src("palette")}
              alt=""
              fill
              sizes="(min-width: 1024px) 55vw, 100vw"
              className="object-cover"
            />
          </div>
          <h3 className="font-display text-headline mt-4 font-bold lg:text-[2.5rem]">
            {t("shop")}
          </h3>
          <p className="text-prune-doux max-w-[46ch]">{t("shopText")}</p>
        </Link>
        <Link href="/academie" className="press block lg:col-span-4 lg:col-start-9 lg:mt-24">
          <div className="rounded-photo bg-poudre relative aspect-[4/5] overflow-hidden">
            <AutoplayVideo
              src={MEDIA["video-brushes"]!.src}
              poster={MEDIA["video-brushes"]!.poster}
              className="absolute inset-0 z-10 size-full object-cover"
            />
            <Image
              src={MEDIA["video-brushes"]!.poster!}
              alt=""
              fill
              unoptimized
              sizes="(min-width: 1024px) 30vw, 100vw"
              className="object-cover"
            />
          </div>
          <h3 className="font-display text-headline mt-4 font-bold lg:text-[2.5rem]">
            {t("academy")}
          </h3>
          <p className="text-prune-doux max-w-[46ch]">{t("academyText")}</p>
        </Link>
      </div>
    </EditorialSection>
  );
}

function Gift() {
  const t = useTranslations("home.public.gift");
  const alt = useTranslations("home.public.alt");
  return (
    <EditorialSection
      ambiance="hibiscus"
      aria-labelledby="gift-title"
      className="grid lg:grid-cols-[1fr_32%]"
    >
      <div className="flex flex-col justify-center gap-8 px-4 py-16 lg:px-10">
        <h2
          id="gift-title"
          className="font-display text-[2.5rem] leading-[1.05] font-black text-balance hyphens-none lg:text-[5.5rem]"
        >
          {t("title")}
        </h2>
        <Link
          href="/offrir"
          className="press bg-carte text-hibiscus text-lead inline-flex min-h-14 w-fit items-center rounded-full px-7 font-bold"
        >
          {t("cta")}
        </Link>
      </div>
      <div className="relative min-h-[420px] lg:min-h-[620px]">
        <Image
          src={src("headwrap-mural")}
          alt={alt("gift")}
          fill
          sizes="(min-width: 1024px) 32vw, 100vw"
          className="object-cover"
        />
      </div>
    </EditorialSection>
  );
}

function Closing() {
  const t = useTranslations("home.public.footer");
  return (
    <EditorialSection
      ambiance="nuit"
      className="overflow-hidden px-4 pt-10 pb-28 lg:px-10 lg:pb-10"
    >
      <footer className="flex flex-col gap-6">
        <Monument className="text-center text-[29.5vw] lg:text-left lg:text-[17vw]" />
        <p className="text-lead text-prune-doux">{PLACES}</p>
        <nav
          aria-label={t("label")}
          className="text-small flex flex-wrap items-center gap-x-6 gap-y-1 font-bold"
        >
          <Link href="/aide" className="inline-flex min-h-12 items-center">
            {t("help")}
          </Link>
          <Link href="/pages/conditions-generales" className="inline-flex min-h-12 items-center">
            {t("terms")}
          </Link>
          <Link href="/pages/confidentialite" className="inline-flex min-h-12 items-center">
            {t("privacy")}
          </Link>
          <a href="/media/CREDITS.md" className="inline-flex min-h-12 items-center">
            {t("credits")}
          </a>
        </nav>
        <LocaleSwitcher />
      </footer>
    </EditorialSection>
  );
}

/** Home of a visitor: an edge-to-edge magazine, then the real feed of the pros. */
export function PublicHome({ feed }: { feed: ReactNode }) {
  const t = useTranslations("common");
  const tHome = useTranslations("home.public.feed");
  const locale = useLocale();
  const icons = navIcons();
  return (
    <>
      <a
        href="#main"
        className="bg-hibiscus text-sur-hibiscus sr-only z-50 rounded-full px-5 py-3 font-bold focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        {t("skipToContent")}
      </a>
      <main id="main" lang={locale}>
        <Opening />
        <Hands />
        <ReceiptCode />
        <Booking />
        <ShopAndAcademy />
        <Gift />
        <EditorialSection aria-labelledby="feed-title" className="px-4 py-16 lg:py-24">
          <div className="mx-auto flex max-w-[640px] flex-col gap-8">
            <div className="flex items-center justify-between gap-3">
              <h2 id="feed-title" className="font-display text-display font-black">
                {tHome("title")}
              </h2>
              <CityPicker />
            </div>
            {feed}
          </div>
        </EditorialSection>
        <Closing />
      </main>
      <BottomNav icons={icons} />
    </>
  );
}
