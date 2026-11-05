import { useTranslations } from "next-intl";
import Image from "next/image";

import { TITLE, TopBar } from "@/components/features/marketing/chrome";
import { TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

const MEDIA = library as Record<string, { src: string }>;

/** Each photo has its own focus, so that the ticket never covers a face. */
const PHOTOS: Record<Trade, { photo: string; focus: string }> = {
  braids: { photo: "braids-yellow", focus: "62% 12%" },
  hair: { photo: "hero-afro-profile", focus: "50% 8%" },
  makeup: { photo: "makeup-portrait", focus: "60% 20%" },
  nails: { photo: "nails-lips", focus: "60% 20%" },
  sewing: { photo: "sewing", focus: "70% 50%" },
  headwrap: { photo: "headwrap-smile", focus: "50% 6%" },
  skincare: { photo: "skin-warm", focus: "60% 20%" },
};
const FIRST: Trade = "braids";
const ORDER: Trade[] = [FIRST, ...TRADES.filter((trade) => trade !== FIRST)];
const TIMES = ["morning", "noon", "evening"] as const;

const CHOICE =
  "press peer-checked:bg-encre peer-checked:text-blanc peer-focus-visible:outline-hibiscus bg-poudre rounded-button text-small flex min-h-11 cursor-pointer items-center justify-center px-3 font-semibold peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2";

/** What the visitor does first: choose, and the ticket of the appointment prints itself. */
function Ticket() {
  const t = useTranslations("landing.ticket");
  const tTrades = useTranslations("trades");
  const tHome = useTranslations("home.public");
  return (
    <div className="relative z-10 mx-4 -mt-36 mb-6 drop-shadow-xl md:m-6 xl:absolute xl:bottom-8 xl:left-[calc(50%-10rem)] xl:m-0 xl:w-[24rem]">
      <div data-ui data-ambiance="papier" className="sg-ticket rounded-card flex flex-col">
        <div className="flex flex-col gap-3 p-4 pb-5">
          <fieldset className="min-w-0">
            <legend className="text-small mb-2 font-semibold">{t("trade")}</legend>
            <ul className="flex flex-wrap gap-1.5">
              {ORDER.map((trade) => (
                <li key={trade} className="relative">
                  <input
                    type="radio"
                    name="home-trade"
                    id={`trade-${trade}`}
                    value={trade}
                    defaultChecked={trade === FIRST}
                    className="peer sr-only"
                  />
                  <label htmlFor={`trade-${trade}`} className={CHOICE}>
                    {tTrades(trade)}
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
          <fieldset className="min-w-0">
            <legend className="text-small mb-2 font-semibold">{t("time")}</legend>
            <ul className="grid grid-cols-3 gap-1.5">
              {TIMES.map((time) => (
                <li key={time} className="relative">
                  <input
                    type="radio"
                    name="home-time"
                    id={`time-${time}`}
                    value={time}
                    defaultChecked={time === "noon"}
                    className="peer sr-only"
                  />
                  <label htmlFor={`time-${time}`} className={CHOICE}>
                    {t(`times.${time}`)}
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
        </div>
        <div className="sg-ticket-foot border-trait flex flex-col justify-between gap-3 border-t-2 border-dashed p-4">
          <div className="flex min-h-0 items-center gap-4">
            <div className="size-[7.5rem] shrink-0">
              {ORDER.map((trade) => (
                <Image
                  key={trade}
                  data-show={trade}
                  src={`/brand/qr/${trade}.svg`}
                  alt={t("qrAlt", { trade: tTrades(trade) })}
                  width={120}
                  height={120}
                  unoptimized
                  className="sg-qr-print size-full"
                />
              ))}
            </div>
            <div className="min-w-0">
              {ORDER.map((trade) => (
                <p key={trade} data-show={trade} className="font-display text-title">
                  {tTrades(trade)}
                </p>
              ))}
              {TIMES.map((time) => (
                <p key={time} data-time={time} className="font-semibold">
                  {t(`when.${time}`)}
                </p>
              ))}
              <p className="text-small text-prune-doux mt-1">{t("show")}</p>
            </div>
          </div>
          {ORDER.map((trade) => (
            <div key={trade} data-show={trade}>
              <Button asChild fullWidth>
                <Link href={{ pathname: "/explore", query: { trade } }}>
                  {tHome(`find.${trade}`)}
                </Link>
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** First screen: what it is in three words, and the ticket that shows it instead of saying it. */
export function Hero() {
  const t = useTranslations("landing.hero");
  const tHome = useTranslations("home.public");
  const tMarketing = useTranslations("marketing");
  return (
    <EditorialSection
      ambiance="rouge"
      aria-labelledby="home-title"
      className="sg-chooser relative flex flex-col overflow-clip xl:grid xl:min-h-[max(100svh,52rem)] xl:grid-cols-2"
    >
      <TopBar />
      <div className="relative z-10 flex flex-col gap-5 px-4 pt-[5.5rem] pb-8 md:px-8 md:pt-24 xl:gap-6 xl:px-10 xl:pt-32 xl:pb-10">
        <div className="flex items-start justify-between gap-2 xl:max-w-[calc(50vw-5rem)]">
          <h1
            id="home-title"
            className={`${TITLE} text-[clamp(2.5rem,11.6vw,3.25rem)] leading-[0.96] md:text-[4.5rem] xl:text-[clamp(4rem,6vw,7rem)]`}
          >
            <span className="sg-mask">
              <span>{t("first")}</span>
            </span>
            <span className="sg-mask">
              <span style={{ "--line": 1 } as React.CSSProperties}>{t("second")}</span>
            </span>
          </h1>
          <SpeakButton text={`${t("first")} ${t("second")}`} />
        </div>
        <p className="sg-after-title text-lead max-w-[27rem] xl:mt-auto">{t("line")}</p>
        <div className="sg-after-title grid grid-cols-2 gap-2 sm:flex xl:max-w-[27rem]">
          <Button asChild variant="secondary" className="text-small px-2 sm:px-5">
            <Link href="/proposer-mes-services">{tMarketing("iAmPro")}</Link>
          </Button>
          <Button asChild variant="secondary" className="text-small px-2 sm:hidden">
            <Link href="/auth?as=client">{tMarketing("createAccount")}</Link>
          </Button>
        </div>
      </div>
      <div className="grid md:grid-cols-2 xl:contents">
        <div className="relative aspect-square overflow-clip md:aspect-auto md:min-h-[36rem] xl:col-start-2 xl:row-start-1">
          {ORDER.map((trade, index) => (
            <div key={trade} data-show={trade} className="absolute inset-0">
              <Image
                src={MEDIA[PHOTOS[trade].photo]!.src}
                alt={tHome(`alt.${trade}`)}
                fill
                priority={index === 0}
                loading={index === 0 ? undefined : "lazy"}
                sizes="(min-width: 768px) 50vw, 100vw"
                className="sg-photo-settle object-cover"
                style={{ objectPosition: PHOTOS[trade].focus }}
              />
            </div>
          ))}
        </div>
        <Ticket />
      </div>
    </EditorialSection>
  );
}
