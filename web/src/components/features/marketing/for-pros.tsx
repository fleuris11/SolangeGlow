import { CheckCircle } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import Image from "next/image";

import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

import { lines, MarketingPage, TITLE, TopBar } from "./chrome";
import { QrPoster } from "./qr-poster";

const MEDIA = library as Record<string, { src: string }>;
const CHAPTERS = [
  { key: "showcase", photo: "braids-hoops", alt: "braids" },
  { key: "agenda", photo: "salon-pink", alt: "salon" },
  { key: "shop", photo: "palette", alt: "palette" },
  { key: "academy", photo: "braider-hands", alt: "hands" },
  { key: "social", photo: "curls-teal", alt: "curls" },
] as const;

function Ticks({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-3">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3">
          <CheckCircle
            aria-hidden
            size={24}
            weight="fill"
            className="text-feuille mt-0.5 shrink-0"
          />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Everything a pro gets, what is free and how to start, for someone who has no account yet. */
export function ForProsPage({ signedIn }: { signedIn: boolean }) {
  const t = useTranslations("marketing.pros");
  return (
    <MarketingPage>
      <EditorialSection
        ambiance="nuit"
        aria-labelledby="pros-title"
        className="relative flex min-h-[calc(100svh-4rem)] flex-col justify-end overflow-clip pt-[56vw] lg:min-h-svh lg:pt-28"
      >
        <TopBar signedIn={signedIn} />
        <div className="absolute inset-0 lg:left-[34%]">
          <Image
            src={MEDIA["nails-pro"]!.src}
            alt={t("heroAlt")}
            fill
            priority
            sizes="(min-width: 1024px) 66vw, 100vw"
            className="object-cover"
          />
        </div>
        <div
          aria-hidden
          className="from-nuit via-nuit/60 lg:via-nuit/70 absolute inset-0 bg-linear-to-t to-transparent to-80% lg:bg-linear-to-r lg:from-34% lg:via-46% lg:to-62%"
        />
        <div
          aria-hidden
          className="from-nuit/70 absolute inset-x-0 top-0 h-28 bg-linear-to-b to-transparent lg:h-36"
        />
        <div className="relative z-10 flex flex-col gap-5 px-4 pb-6 lg:max-w-[50%] lg:px-10 lg:pb-12">
          <div className="flex items-start justify-between gap-2">
            <h1
              id="pros-title"
              className={`${TITLE} text-[2.75rem] leading-[1.04] lg:text-[clamp(3.5rem,5.4vw,5.5rem)]`}
            >
              {t("title")}
            </h1>
            <SpeakButton text={t("title")} />
          </div>
          <p className="text-lead max-w-[38ch]">{t("line")}</p>
          <Button asChild size="lg" className="w-full lg:w-fit">
            <Link href="/auth?as=pro">{t("cta")}</Link>
          </Button>
        </div>
      </EditorialSection>

      <EditorialSection aria-labelledby="pros-who" className="px-4 py-16 lg:px-10 lg:py-24">
        <h2 id="pros-who" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[4.5rem]`}>
          {t("who.title")}
        </h2>
        <ul className="border-trait mt-8 grid border-t lg:grid-cols-3 lg:gap-8 lg:border-t-0">
          {(["solo", "salon", "staff"] as const).map((kind) => (
            <li key={kind} className="border-trait border-b py-6 lg:border-t lg:border-b-0">
              <h3 className="font-display text-title">{t(`who.${kind}.title`)}</h3>
              <p className="text-prune-doux mt-2">{t(`who.${kind}.text`)}</p>
            </li>
          ))}
        </ul>
      </EditorialSection>

      <EditorialSection
        ambiance="nuit"
        aria-labelledby="pros-qr"
        className="grid grid-cols-[minmax(0,1fr)] gap-10 px-4 py-16 lg:grid-cols-[minmax(0,1fr)_auto] lg:gap-20 lg:px-10 lg:py-24"
      >
        <div className="flex flex-col gap-6">
          <h2 id="pros-qr" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[4.5rem]`}>
            {t("qr.title")}
          </h2>
          <p className="text-lead max-w-[40ch]">{t("qr.text")}</p>
          <Ticks items={lines(t, "qr.items")} />
        </div>
        <QrPoster className="max-w-[320px]" />
      </EditorialSection>

      {CHAPTERS.map(({ key, photo, alt }, index) => (
        <EditorialSection
          key={key}
          ambiance={index % 2 ? "poudre" : "jour"}
          aria-labelledby={`pros-${key}`}
          className="grid lg:grid-cols-2"
        >
          <div className="flex flex-col justify-center gap-6 px-4 py-14 lg:px-10 lg:py-24">
            <h2
              id={`pros-${key}`}
              className={`${TITLE} text-[2.25rem] leading-[1.08] lg:text-[3.5rem]`}
            >
              {t(`${key}.title`)}
            </h2>
            <Ticks items={lines(t, `${key}.items`)} />
          </div>
          <div
            className={`relative min-h-[320px] lg:min-h-[620px] ${index % 2 ? "lg:order-first" : ""}`}
          >
            <Image
              src={MEDIA[photo]!.src}
              alt={t(`alt.${alt}`)}
              fill
              sizes="(min-width: 1024px) 50vw, 100vw"
              className="object-cover"
            />
          </div>
        </EditorialSection>
      ))}

      <EditorialSection aria-labelledby="pros-plans" className="px-4 py-16 lg:px-10 lg:py-24">
        <h2 id="pros-plans" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[4.5rem]`}>
          {t("plans.title")}
        </h2>
        <div className="mt-10 grid gap-10 lg:grid-cols-2 lg:gap-16">
          <section aria-labelledby="plan-free" className="flex flex-col gap-4">
            <h3 id="plan-free" className="font-display text-headline">
              {t("plans.free")}
            </h3>
            <Ticks items={lines(t, "plans.freeItems")} />
          </section>
          <section aria-labelledby="plan-premium" className="flex flex-col gap-4">
            <h3 id="plan-premium" className="font-display text-headline">
              {t("plans.premium")}
            </h3>
            <Ticks items={lines(t, "plans.premiumItems")} />
            <p className="text-prune-doux">{t("plans.trial")}</p>
          </section>
        </div>
        <p className="border-trait text-prune-doux mt-10 max-w-[64ch] border-t pt-6">
          {t("plans.note")}
        </p>
      </EditorialSection>

      <EditorialSection
        ambiance="hibiscus"
        aria-labelledby="pros-start"
        className="flex flex-col gap-8 px-4 py-16 lg:px-10 lg:py-24"
      >
        <h2 id="pros-start" className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[4.5rem]`}>
          {t("start.title")}
        </h2>
        <ol className="grid gap-6 lg:grid-cols-3 lg:gap-12">
          {lines(t, "start.steps").map((step, index) => (
            <li key={step} className="flex gap-4">
              <span aria-hidden className="font-display text-headline leading-none">
                {index + 1}
              </span>
              <span className="text-lead">{step}</span>
            </li>
          ))}
        </ol>
        <Link
          href="/auth?as=pro"
          className="press bg-sur-hibiscus text-rouge rounded-button text-lead inline-flex min-h-14 w-fit items-center px-7 font-semibold"
        >
          {t("cta")}
        </Link>
      </EditorialSection>
    </MarketingPage>
  );
}
