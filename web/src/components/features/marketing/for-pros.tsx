import { Check } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import Image from "next/image";

import { StepsWatcher } from "@/components/features/home/steps-watcher";
import "@/components/features/home/home.css";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

import { lines, MarketingPage, TITLE, TopBar } from "./chrome";
import { QrPoster } from "./qr-poster";

const MEDIA = library as Record<string, { src: string }>;
const CHAPTERS = [
  { key: "showcase", id: "page", photo: "braids-hoops", alt: "braids" },
  { key: "agenda", id: "agenda", photo: "salon-pink", alt: "salon" },
  { key: "shop", id: "shop", photo: "wax-rolls", alt: "palette" },
  { key: "academy", id: "academy", photo: "bride-makeup-gold", alt: "hands" },
  { key: "social", id: "social", photo: "curls-teal", alt: "curls" },
] as const;

function Ticks({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3">
          <Check aria-hidden size={20} weight="bold" className="mt-1 shrink-0" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Everything someone who offers services gets, what is free and how to start. */
export function ForProsPage({ signedIn }: { signedIn: boolean }) {
  const t = useTranslations("marketing.pros");
  return (
    <MarketingPage>
      <EditorialSection
        ambiance="rouge"
        aria-labelledby="pros-title"
        className="relative flex flex-col overflow-clip xl:grid xl:min-h-svh xl:grid-cols-2"
      >
        <TopBar signedIn={signedIn} />
        <div className="relative z-10 flex flex-col gap-5 px-4 pt-[5.5rem] pb-8 md:px-8 md:pt-24 xl:gap-6 xl:px-10 xl:pt-32 xl:pb-10">
          <div className="flex items-start justify-between gap-2">
            <h1
              id="pros-title"
              className={`${TITLE} text-[clamp(2rem,9vw,3rem)] leading-none md:text-[3.5rem] xl:text-[clamp(3rem,4.2vw,5rem)]`}
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
          <Button asChild size="lg" className="sg-after-title w-full sm:w-fit">
            <Link href="/auth?as=pro">{t("cta")}</Link>
          </Button>
        </div>
        <div className="relative aspect-[4/3] overflow-clip md:aspect-video xl:col-start-2 xl:row-start-1 xl:aspect-auto">
          <Image
            src={MEDIA["braider-hands"]!.src}
            alt={t("heroAlt")}
            fill
            priority
            sizes="(min-width: 1280px) 50vw, 100vw"
            className="sg-photo-settle object-cover"
          />
        </div>
      </EditorialSection>

      <EditorialSection
        aria-labelledby="pros-who"
        className="grid gap-8 px-4 py-16 md:px-8 xl:grid-cols-12 xl:gap-x-8 xl:px-10 xl:py-24"
      >
        <h2 id="pros-who" className={`${TITLE} text-headline xl:text-display xl:col-span-3`}>
          {t("who.title")}
        </h2>
        <ul className="grid gap-8 md:grid-cols-3 xl:col-span-9">
          {(["solo", "salon", "staff"] as const).map((kind, index) => (
            <li key={kind} className="sg-rise" style={{ "--i": index } as React.CSSProperties}>
              <h3 className="font-display text-title">{t(`who.${kind}.title`)}</h3>
              <p className="mt-2">{t(`who.${kind}.text`)}</p>
            </li>
          ))}
        </ul>
      </EditorialSection>

      <EditorialSection
        ambiance="nuit"
        aria-labelledby="pros-qr"
        className="grid grid-cols-[minmax(0,1fr)] gap-10 px-4 py-16 md:grid-cols-[minmax(0,1fr)_auto] md:px-8 xl:gap-20 xl:px-10 xl:py-24"
      >
        <div className="flex flex-col gap-6">
          <h2
            id="pros-qr"
            className={`${TITLE} text-[clamp(2.25rem,9vw,3rem)] leading-none xl:text-[clamp(3rem,4.2vw,5rem)]`}
          >
            {t("qr.title")}
          </h2>
          <p className="text-lead max-w-[40ch]">{t("qr.text")}</p>
          <Ticks items={lines(t, "qr.items")} />
        </div>
        <QrPoster className="max-w-[320px]" />
      </EditorialSection>

      <div
        id="chapitres"
        data-active="0"
        className="sg-steps grid gap-x-16 px-4 md:px-8 xl:grid-cols-12 xl:px-10"
      >
        <div className="sticky top-[12vh] hidden h-[76vh] self-start overflow-clip xl:col-span-6 xl:mt-24 xl:block">
          {CHAPTERS.map(({ key, photo, alt }, index) => (
            <div key={key} data-state={index} className="absolute inset-0">
              <Image
                src={MEDIA[photo]!.src}
                alt={t(`alt.${alt}`)}
                fill
                loading="lazy"
                sizes="50vw"
                className="object-cover"
              />
            </div>
          ))}
        </div>
        <div className="xl:col-span-6 xl:pb-24">
          {CHAPTERS.map(({ key, id, photo, alt }, index) => (
            <EditorialSection
              key={key}
              id={id}
              data-step={index}
              aria-labelledby={`pros-${key}`}
              className="flex scroll-mt-4 flex-col justify-center gap-5 py-10 xl:min-h-[66vh] xl:py-0"
            >
              <div className="relative aspect-[4/3] overflow-clip xl:hidden">
                <Image
                  src={MEDIA[photo]!.src}
                  alt={t(`alt.${alt}`)}
                  fill
                  loading="lazy"
                  sizes="100vw"
                  className="object-cover"
                />
              </div>
              <h2
                id={`pros-${key}`}
                className={`${TITLE} text-prune text-headline xl:text-display`}
              >
                {t(`${key}.title`)}
              </h2>
              <div className="text-prune">
                <Ticks items={lines(t, `${key}.items`)} />
              </div>
            </EditorialSection>
          ))}
        </div>
        <StepsWatcher target="chapitres" />
      </div>

      <EditorialSection
        aria-labelledby="pros-plans"
        ambiance="poudre"
        className="px-4 py-16 md:px-8 xl:px-10 xl:py-24"
      >
        <h2 id="pros-plans" className={`${TITLE} text-headline xl:text-display`}>
          {t("plans.title")}
        </h2>
        <div className="mt-8 grid gap-10 md:grid-cols-2 xl:gap-16">
          <section aria-labelledby="plan-free" className="flex flex-col gap-4">
            <h3 id="plan-free" className="font-display text-title">
              {t("plans.free")}
            </h3>
            <Ticks items={lines(t, "plans.freeItems")} />
          </section>
          <section aria-labelledby="plan-premium" className="flex flex-col gap-4">
            <h3 id="plan-premium" className="font-display text-title">
              {t("plans.premium")}
            </h3>
            <Ticks items={lines(t, "plans.premiumItems")} />
            <p>{t("plans.trial")}</p>
          </section>
        </div>
        <p className="mt-8 max-w-[64ch]">{t("plans.note")}</p>
      </EditorialSection>

      <EditorialSection
        ambiance="rouge"
        aria-labelledby="pros-start"
        className="flex flex-col gap-8 px-4 py-16 md:px-8 xl:px-10 xl:py-24"
      >
        <h2
          id="pros-start"
          className={`${TITLE} text-[clamp(2.25rem,9vw,3rem)] leading-none xl:text-[clamp(3rem,4.2vw,5rem)]`}
        >
          {t("start.title")}
        </h2>
        <ol className="grid gap-6 md:grid-cols-3 xl:gap-12">
          {lines(t, "start.steps").map((step, index) => (
            <li key={step} className="flex gap-4">
              <span aria-hidden className="font-display text-headline leading-none">
                {index + 1}
              </span>
              <span className="text-lead">{step}</span>
            </li>
          ))}
        </ol>
        <Button asChild size="lg" className="w-full sm:w-fit">
          <Link href="/auth?as=pro">{t("cta")}</Link>
        </Button>
      </EditorialSection>
    </MarketingPage>
  );
}
