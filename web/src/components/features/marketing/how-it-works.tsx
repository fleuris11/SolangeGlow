import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";

import { lines, MarketingPage, TITLE, TopBar } from "./chrome";

const ACCOUNTS = ["guest", "client", "solo", "salon", "staff"] as const;
const JOURNEYS = [
  { key: "booking", id: "rendez-vous", href: "/explore" },
  { key: "payment", id: "payer", href: "/explore" },
  { key: "france", id: "france", href: "/selection" },
  { key: "gift", id: "offrir", href: "/offrir" },
  { key: "academy", id: "academie", href: "/academie" },
  { key: "games", id: "jeux", href: "/classements" },
] as const;

const JUMP =
  "press bg-lait text-prune rounded-button text-small inline-flex min-h-11 items-center px-3 font-semibold";

/** Who can do what, how to create an account, and each journey, step by step. */
export function HowItWorksPage({ signedIn }: { signedIn: boolean }) {
  const t = useTranslations("marketing.how");
  const tNav = useTranslations("marketing");
  return (
    <MarketingPage>
      <EditorialSection
        ambiance="rouge"
        aria-labelledby="how-title"
        className="relative flex flex-col gap-6 px-4 pt-[5.5rem] pb-12 md:px-8 md:pt-24 xl:px-10 xl:pt-32 xl:pb-16"
      >
        <TopBar signedIn={signedIn} />
        <div className="flex items-start justify-between gap-2">
          <h1
            id="how-title"
            className={`${TITLE} text-[clamp(2.5rem,11vw,3.25rem)] leading-none md:text-[4.5rem] xl:text-[clamp(4rem,6vw,7rem)]`}
          >
            {t("title")}
          </h1>
          <SpeakButton text={t("title")} />
        </div>
        <p className="text-lead max-w-[46ch]">{t("line")}</p>
        <nav
          aria-label={t("jump")}
          data-ambiance="papier"
          className="flex flex-wrap gap-2 bg-transparent!"
        >
          <a href="#comptes" className={JUMP}>
            {t("accounts.title")}
          </a>
          {JOURNEYS.map(({ key, id }) => (
            <a key={key} href={`#${id}`} className={JUMP}>
              {t(`${key}.short`)}
            </a>
          ))}
          <a href="#audio" className={JUMP}>
            {t("audio.short")}
          </a>
        </nav>
      </EditorialSection>

      <EditorialSection
        id="comptes"
        aria-labelledby="accounts-title"
        className="scroll-mt-4 px-4 py-16 md:px-8 xl:px-10 xl:py-24"
      >
        <h2 id="accounts-title" className={`${TITLE} text-headline xl:text-display`}>
          {t("accounts.title")}
        </h2>
        <p className="text-lead mt-3 max-w-[52ch]">{t("accounts.line")}</p>
        <ul className="mt-8 flex flex-col gap-2">
          {ACCOUNTS.map((kind) => (
            <li
              key={kind}
              className="bg-poudre rounded-card grid gap-3 p-4 xl:grid-cols-[1fr_2fr_1.2fr] xl:gap-10 xl:p-6"
            >
              <h3 className="font-display text-title">{t(`accounts.${kind}.title`)}</h3>
              <p>
                <span className="block font-semibold">{t("accounts.can")}</span>
                {t(`accounts.${kind}.can`)}
              </p>
              <p>
                <span className="block font-semibold">{t("accounts.cannot")}</span>
                {t(`accounts.${kind}.cannot`)}
              </p>
            </li>
          ))}
        </ul>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/auth?as=client">{tNav("createAccount")}</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/proposer-mes-services">{tNav("iAmPro")}</Link>
          </Button>
        </div>
      </EditorialSection>

      <EditorialSection
        ambiance="nuit"
        aria-labelledby="signup-title"
        className="px-4 py-16 md:px-8 xl:px-10 xl:py-24"
      >
        <h2 id="signup-title" className={`${TITLE} text-headline xl:text-display`}>
          {t("signup.title")}
        </h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-3 xl:gap-12">
          {lines(t, "signup.steps").map((step, index) => (
            <li key={step} className="flex gap-4">
              <span aria-hidden className="font-display text-headline leading-none">
                {index + 1}
              </span>
              <span className="text-lead">{step}</span>
            </li>
          ))}
        </ol>
        <p className="mt-8 max-w-[60ch]">{t("signup.note")}</p>
      </EditorialSection>

      {JOURNEYS.map(({ key, id, href }, index) => (
        <EditorialSection
          key={key}
          id={id}
          ambiance={index % 2 ? "poudre" : "jour"}
          aria-labelledby={`${id}-title`}
          className="grid scroll-mt-4 gap-6 px-4 py-16 md:px-8 xl:grid-cols-12 xl:gap-x-16 xl:px-10 xl:py-24"
        >
          <div className="flex flex-col items-start gap-5 xl:col-span-5">
            <div className="flex w-full items-start justify-between gap-2">
              <h2 id={`${id}-title`} className={`${TITLE} text-headline xl:text-display`}>
                {t(`${key}.title`)}
              </h2>
              <SpeakButton text={t(`${key}.title`)} />
            </div>
            <Button asChild variant="secondary" className="max-xl:hidden">
              <Link href={href}>{t(`${key}.cta`)}</Link>
            </Button>
          </div>
          <ol className="flex flex-col gap-4 xl:col-span-7">
            {lines(t, `${key}.steps`).map((step, stepIndex) => (
              <li key={step} className="flex gap-4">
                <span
                  aria-hidden
                  className="font-display text-title w-6 shrink-0 leading-none tabular-nums"
                >
                  {stepIndex + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <Button asChild variant="secondary" className="xl:hidden">
            <Link href={href}>{t(`${key}.cta`)}</Link>
          </Button>
        </EditorialSection>
      ))}

      <EditorialSection
        id="audio"
        ambiance="rouge"
        aria-labelledby="audio-title"
        className="grid scroll-mt-4 gap-6 px-4 py-16 md:px-8 xl:grid-cols-12 xl:gap-x-16 xl:px-10 xl:py-24"
      >
        <h2 id="audio-title" className={`${TITLE} text-headline xl:text-display xl:col-span-5`}>
          {t("audio.title")}
        </h2>
        <ul className="text-lead flex flex-col gap-3 xl:col-span-7">
          {lines(t, "audio.items").map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </EditorialSection>
    </MarketingPage>
  );
}
