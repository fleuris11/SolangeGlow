import {
  CalendarCheck,
  ChatsCircle,
  GameController,
  Gift as GiftIcon,
  GraduationCap,
  MapPin,
  QrCode,
  ShieldCheck,
  SpeakerHigh,
  Storefront,
  VideoCamera,
  ImagesSquare,
} from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import Image from "next/image";
import type { ReactNode } from "react";

import { lines, MarketingPage, TITLE, TopBar } from "@/components/features/marketing/chrome";
import { QrPoster } from "@/components/features/marketing/qr-poster";
import { TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { CityPicker } from "@/components/shell/city-picker";
import { AutoplayVideo } from "@/components/ui/autoplay-video";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { ParallaxImage } from "@/components/ui/parallax-image";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

type Photo = keyof typeof library;
const MEDIA = library as Record<string, { src: string; poster?: string }>;

/** The whole screen is the photo: each one has its own focus, away from the words. */
const TRADE_PHOTOS: Record<Trade, { photo: Photo; focus: string }> = {
  braids: { photo: "braids-yellow", focus: "60% 18%" },
  hair: { photo: "hero-afro-profile", focus: "50% 20%" },
  makeup: { photo: "makeup-portrait", focus: "50% 20%" },
  nails: { photo: "nails-lips", focus: "50% 40%" },
  sewing: { photo: "sewing", focus: "50% 50%" },
  headwrap: { photo: "hero-orange-hat", focus: "50% 12%" },
  skincare: { photo: "skin-warm", focus: "50% 30%" },
};
const FIRST_TRADE: Trade = "braids";
const ORDER: Trade[] = [FIRST_TRADE, ...TRADES.filter((trade) => trade !== FIRST_TRADE)];
const CODE = ["4", "8", "1", "7", "2", "6"];

/** Each thing the platform does, with where to see it. Nothing here needs a private page. */
const EVERYTHING = [
  { key: "find", href: "/explore", icon: MapPin },
  { key: "book", href: "/explore", icon: CalendarCheck },
  { key: "qr", href: "/comment-ca-marche#rendez-vous", icon: QrCode },
  { key: "feed", href: "#feed-title", icon: ImagesSquare },
  { key: "talk", href: "/comment-ca-marche#comptes", icon: ChatsCircle },
  { key: "shop", href: "/comment-ca-marche#payer", icon: ShieldCheck },
  { key: "live", href: "/academie/lives", icon: VideoCamera },
  { key: "france", href: "/selection", icon: Storefront },
  { key: "academy", href: "/academie", icon: GraduationCap },
  { key: "gift", href: "/offrir", icon: GiftIcon },
  { key: "games", href: "/classements", icon: GameController },
  { key: "audio", href: "/comment-ca-marche#audio", icon: SpeakerHigh },
] as const;

const DOORS = [
  { key: "guest", photo: "bride-makeup", href: "/explore", primary: false },
  { key: "client", photo: "curls-blue", href: "/auth?as=client", primary: true },
  { key: "pro", photo: "nails-pro", href: "/auth?as=pro", primary: false },
] as const;

const QUESTIONS = ["account", "signup", "pro", "qr", "payment", "france"] as const;

function src(photo: Photo) {
  return MEDIA[photo]!.src;
}

/**
 * The opening: the photo fills the screen. Choosing a trade changes it, and the button, with
 * native radio buttons and CSS only (globals.css, .sg-chooser): no script, keyboard included,
 * and a picture that is not shown is not downloaded.
 */
function Opening() {
  const t = useTranslations("home.public");
  const tMarketing = useTranslations("marketing");
  const tTrades = useTranslations("trades");
  return (
    <EditorialSection
      ambiance="nuit"
      aria-labelledby="home-title"
      className="sg-chooser relative flex min-h-[calc(100svh-4rem)] flex-col justify-end overflow-clip pt-[56vw] lg:min-h-svh lg:pt-28"
    >
      <TopBar />
      {ORDER.map((trade, index) => (
        <div key={trade} data-show={trade} className="absolute inset-0 lg:left-[34%]">
          <Image
            src={src(TRADE_PHOTOS[trade].photo)}
            alt={t(`alt.${trade}`)}
            fill
            priority={index === 0}
            loading={index === 0 ? undefined : "lazy"}
            sizes="(min-width: 1024px) 66vw, 100vw"
            className="object-cover"
            style={{ objectPosition: TRADE_PHOTOS[trade].focus }}
          />
        </div>
      ))}
      <div
        aria-hidden
        className="from-nuit via-nuit/40 lg:via-nuit/70 absolute inset-0 bg-linear-to-t to-transparent to-75% lg:bg-linear-to-r lg:from-34% lg:via-46% lg:to-62%"
      />
      <div
        aria-hidden
        className="from-nuit/70 absolute inset-x-0 top-0 h-28 bg-linear-to-b to-transparent lg:h-36"
      />

      <div className="relative z-10 flex flex-col gap-4 px-4 pb-6 lg:max-w-[48%] lg:gap-6 lg:px-10 lg:pb-12">
        <div className="sg-line-up flex items-start justify-between gap-2">
          <h1
            id="home-title"
            className={`${TITLE} text-[2.75rem] leading-[1.04] lg:text-[clamp(3.5rem,6vw,6rem)]`}
          >
            {t("title")}
          </h1>
          <SpeakButton text={t("title")} />
        </div>
        <p className="sg-line-up text-lead max-w-[36ch] [--line:1]">{t("line")}</p>

        <fieldset className="sg-line-up min-w-0 [--line:2]">
          <legend className="sr-only">{t("chooseTrade")}</legend>
          <ul className="-mx-4 flex [scrollbar-width:none] gap-5 overflow-x-auto px-4 lg:mx-0 lg:w-max lg:gap-7 lg:overflow-visible lg:px-0">
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
                  className="peer-checked:border-prune peer-focus-visible:outline-hibiscus flex min-h-12 cursor-pointer items-center border-b-2 border-transparent font-semibold peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2"
                >
                  {tTrades(trade)}
                </label>
              </li>
            ))}
          </ul>
        </fieldset>

        <div className="sg-line-up flex flex-col gap-3 [--line:3] lg:flex-row lg:flex-wrap lg:items-center">
          {ORDER.map((trade) => (
            <div key={trade} data-show={trade}>
              <Button asChild size="lg" className="w-full lg:w-auto">
                <Link href={{ pathname: "/explore", query: { trade } }}>{t(`find.${trade}`)}</Link>
              </Button>
            </div>
          ))}
          <div className="grid grid-cols-2 gap-3 lg:flex">
            <Button asChild variant="secondary" className="text-small px-1 lg:px-5">
              <Link href="/auth?as=client">{tMarketing("createAccount")}</Link>
            </Button>
            <Button asChild variant="secondary" className="text-small px-1 lg:px-5">
              <Link href="/pour-les-pros">{tMarketing("iAmPro")}</Link>
            </Button>
          </div>
        </div>
      </div>
    </EditorialSection>
  );
}

/** The first thing to understand: what you can do without an account, as a client, as a pro. */
function Doors() {
  const t = useTranslations("marketing.who");
  const tMarketing = useTranslations("marketing");
  return (
    <EditorialSection aria-labelledby="who-title" className="px-4 py-16 lg:px-10 lg:py-24">
      <div className="flex items-start justify-between gap-3">
        <h2 id="who-title" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[5rem]`}>
          {t("title")}
        </h2>
        <SpeakButton text={t("title")} />
      </div>
      <ul className="mt-10 grid gap-12 lg:grid-cols-3 lg:gap-8">
        {DOORS.map(({ key, photo, href, primary }) => (
          <li key={key} className="flex flex-col gap-4">
            <div className="rounded-photo relative aspect-[3/2] overflow-hidden">
              <Image
                src={src(photo)}
                alt=""
                fill
                sizes="(min-width: 1024px) 30vw, 100vw"
                className="object-cover"
              />
            </div>
            <h3 className="font-display text-headline">{t(`${key}.title`)}</h3>
            <p className="font-semibold">{t(`${key}.text`)}</p>
            <ul className="text-prune-doux flex flex-1 flex-col gap-1">
              {lines(t, `${key}.items`).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <Button asChild size="lg" variant={primary ? "primary" : "secondary"}>
              <Link href={href}>{t(`${key}.cta`)}</Link>
            </Button>
            {key === "pro" && (
              <Link
                href="/pour-les-pros"
                className="inline-flex min-h-12 items-center justify-center font-semibold underline"
              >
                {t("pro.more")}
              </Link>
            )}
          </li>
        ))}
      </ul>
      <p className="border-trait mt-10 flex flex-wrap items-center gap-x-3 border-t pt-4">
        {t("already")}
        <Link href="/auth" className="inline-flex min-h-12 items-center font-semibold underline">
          {tMarketing("signIn")}
        </Link>
      </p>
    </EditorialSection>
  );
}

/** All the platform on one screen, as an index: an icon and a word, for those who read little. */
function Everything() {
  const t = useTranslations("marketing.everything");
  return (
    <EditorialSection
      ambiance="poudre"
      aria-labelledby="everything-title"
      className="px-4 py-16 lg:px-10 lg:py-24"
    >
      <h2 id="everything-title" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[5rem]`}>
        {t("title")}
      </h2>
      <ul className="border-trait mt-10 grid border-t lg:grid-cols-2 lg:gap-x-16">
        {EVERYTHING.map(({ key, href, icon: Icon }) => (
          <li key={key} className="border-trait border-b">
            {href.startsWith("#") ? (
              <a href={href} className="press flex min-h-20 items-center gap-4 py-4">
                <Icon aria-hidden size={32} weight="duotone" className="text-hibiscus shrink-0" />
                <span className="min-w-0">
                  <span className="text-lead block font-semibold">{t(`${key}.title`)}</span>
                  <span className="text-prune-doux block">{t(`${key}.text`)}</span>
                </span>
              </a>
            ) : (
              <Link href={href} className="press flex min-h-20 items-center gap-4 py-4">
                <Icon aria-hidden size={32} weight="duotone" className="text-hibiscus shrink-0" />
                <span className="min-w-0">
                  <span className="text-lead block font-semibold">{t(`${key}.title`)}</span>
                  <span className="text-prune-doux block">{t(`${key}.text`)}</span>
                </span>
              </Link>
            )}
          </li>
        ))}
      </ul>
      <Button asChild variant="secondary" className="mt-8">
        <Link href="/comment-ca-marche">{t("more")}</Link>
      </Button>
    </EditorialSection>
  );
}

function Print({
  photo,
  alt,
  title,
  text,
  trade,
  sizes,
  className,
}: {
  photo: Photo;
  alt: string;
  title: string;
  text: string;
  trade: Trade;
  sizes: string;
  className: string;
}) {
  return (
    <Link href={{ pathname: "/explore", query: { trade } }} className={`press block ${className}`}>
      <div className="rounded-photo relative aspect-[4/5] overflow-hidden">
        <Image src={src(photo)} alt={alt} fill sizes={sizes} className="object-cover" />
      </div>
      <h3 className="font-display text-title mt-3">{title}</h3>
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
        className={`${TITLE} text-[2.5rem] leading-[1.06] lg:max-w-[14ch] lg:text-[5.5rem]`}
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
          className="col-span-4 lg:col-span-3 lg:col-start-10 lg:-mt-32"
          sizes="(min-width: 1024px) 22vw, 60vw"
        />
      </div>
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
          className={`${TITLE} text-[2.5rem] leading-[1.06] lg:max-w-[18ch] lg:text-[5rem]`}
        >
          {t("title")}
        </h2>
        <SpeakButton text={t("title")} />
      </div>
      <p
        aria-hidden
        className="font-display border-trait my-8 flex justify-between border-y py-4 text-[3.25rem] leading-none lg:my-14 lg:py-8 lg:text-[11vw]"
      >
        {CODE.map((digit, index) => (
          <span key={index}>{digit}</span>
        ))}
      </p>
      <ol className="flex flex-col gap-5 lg:grid lg:grid-cols-3 lg:gap-12">
        {steps.map((step) => (
          <li key={step}>
            <h3 className="text-lead font-semibold">{t(`${step}.title`)}</h3>
            <p className="text-prune-doux">{t(`${step}.text`)}</p>
          </li>
        ))}
      </ol>
    </EditorialSection>
  );
}

function Booking() {
  const t = useTranslations("marketing.booking");
  const alt = useTranslations("home.public.alt");
  return (
    <EditorialSection
      ambiance="poudre"
      aria-labelledby="booking-title"
      className="grid lg:grid-cols-[1fr_55%]"
    >
      <div className="flex flex-col justify-center gap-6 px-4 py-16 lg:px-10">
        <h2 id="booking-title" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[4.5rem]`}>
          {t("title")}
        </h2>
        <ul className="text-lead flex max-w-[40ch] flex-col gap-3">
          {lines(t, "items").map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <Button asChild size="lg" className="w-fit">
          <Link href="/explore">{t("cta")}</Link>
        </Button>
      </div>
      <ParallaxImage
        src={src("bride-afro")}
        alt={alt("booking")}
        sizes="(min-width: 1024px) 55vw, 100vw"
        className="min-h-[440px] lg:min-h-[760px]"
      />
    </EditorialSection>
  );
}

/** Pros: free showcase, QR code to print, agenda, shop. Everything else on their own page. */
function ForPros() {
  const t = useTranslations("marketing.forPros");
  return (
    <EditorialSection
      id="pros"
      ambiance="nuit"
      aria-labelledby="for-pros-title"
      className="grid grid-cols-[minmax(0,1fr)] gap-10 px-4 py-16 lg:grid-cols-[minmax(0,1fr)_auto] lg:gap-20 lg:px-10 lg:py-28"
    >
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-3">
          <h2
            id="for-pros-title"
            className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[5rem]`}
          >
            {t("title")}
          </h2>
          <SpeakButton text={t("title")} />
        </div>
        <p className="text-lead max-w-[42ch]">{t("line")}</p>
        <ul className="border-trait grid border-t lg:grid-cols-2 lg:gap-x-10">
          {lines(t, "items").map((item) => (
            <li key={item} className="border-trait border-b py-3 font-semibold">
              {item}
            </li>
          ))}
        </ul>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/auth?as=pro">{t("cta")}</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/pour-les-pros">{t("more")}</Link>
          </Button>
        </div>
      </div>
      <QrPoster className="max-w-[320px]" />
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
          <div className="rounded-photo bg-poudre relative aspect-[3/2] overflow-hidden">
            <Image
              src={MEDIA["video-makeup-set"]!.poster!}
              alt=""
              fill
              unoptimized
              sizes="(min-width: 1024px) 55vw, 100vw"
              className="object-cover"
            />
            <AutoplayVideo
              src={MEDIA["video-makeup-set"]!.src}
              className="absolute inset-0 size-full object-cover"
            />
          </div>
          <h3 className="font-display text-headline mt-4 lg:text-[2.5rem]">{t("shop")}</h3>
          <p className="text-prune-doux max-w-[46ch]">{t("shopText")}</p>
        </Link>
        <Link href="/academie" className="press block lg:col-span-4 lg:col-start-9 lg:mt-24">
          <div className="rounded-photo bg-poudre relative aspect-[4/5] overflow-hidden">
            <Image
              src={MEDIA["video-brushes"]!.poster!}
              alt=""
              fill
              unoptimized
              sizes="(min-width: 1024px) 30vw, 100vw"
              className="object-cover"
            />
            <AutoplayVideo
              src={MEDIA["video-brushes"]!.src}
              className="absolute inset-0 size-full object-cover"
            />
          </div>
          <h3 className="font-display text-headline mt-4 lg:text-[2.5rem]">{t("academy")}</h3>
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
      className="grid lg:grid-cols-[1fr_36%]"
    >
      <div className="flex flex-col justify-center gap-8 px-4 py-16 lg:px-10">
        <h2 id="gift-title" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[5rem]`}>
          {t("title")}
        </h2>
        <Link
          href="/offrir"
          className="press bg-sur-hibiscus text-rouge rounded-button text-lead inline-flex min-h-14 w-fit items-center px-7 font-semibold"
        >
          {t("cta")}
        </Link>
      </div>
      <div className="relative min-h-[440px] lg:min-h-[640px]">
        <Image
          src={src("headwrap-mural")}
          alt={alt("gift")}
          fill
          sizes="(min-width: 1024px) 36vw, 100vw"
          className="object-cover"
        />
      </div>
    </EditorialSection>
  );
}

function Questions() {
  const t = useTranslations("marketing.questions");
  return (
    <EditorialSection aria-labelledby="questions-title" className="px-4 py-16 lg:px-10 lg:py-24">
      <h2 id="questions-title" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[5rem]`}>
        {t("title")}
      </h2>
      <div className="border-trait mt-10 border-t">
        {QUESTIONS.map((key) => (
          <details key={key} className="border-trait border-b">
            <summary className="text-lead flex min-h-16 cursor-pointer items-center py-3 font-semibold">
              {t(`${key}.q`)}
            </summary>
            <p className="max-w-[64ch] pb-5">{t(`${key}.a`)}</p>
          </details>
        ))}
      </div>
      <Button asChild variant="secondary" className="mt-8">
        <Link href="/aide">{t("help")}</Link>
      </Button>
    </EditorialSection>
  );
}

/** Home of a visitor: who it is for, all it does, real photos, then the real feed of the pros. */
export function PublicHome({ feed }: { feed: ReactNode }) {
  const tHome = useTranslations("home.public.feed");
  return (
    <MarketingPage>
      <Opening />
      <Doors />
      <Everything />
      <Hands />
      <ReceiptCode />
      <Booking />
      <ForPros />
      <ShopAndAcademy />
      <Gift />
      <Questions />
      <EditorialSection aria-labelledby="feed-title" className="px-4 py-16 lg:py-24">
        <div className="mx-auto flex max-w-[640px] flex-col gap-8">
          <div className="flex items-center justify-between gap-3">
            <h2 id="feed-title" className="font-display text-display scroll-mt-4">
              {tHome("title")}
            </h2>
            <CityPicker />
          </div>
          {feed}
        </div>
      </EditorialSection>
    </MarketingPage>
  );
}
