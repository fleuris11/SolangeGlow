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

/** Who can do what, how to create an account, and each journey, step by step. */
export function HowItWorksPage({ signedIn }: { signedIn: boolean }) {
  const t = useTranslations("marketing.how");
  const tNav = useTranslations("marketing");
  return (
    <MarketingPage>
      <EditorialSection
        ambiance="nuit"
        aria-labelledby="how-title"
        className="relative flex flex-col gap-6 px-4 pt-28 pb-12 lg:px-10 lg:pt-40 lg:pb-20"
      >
        <TopBar signedIn={signedIn} />
        <div className="flex items-start justify-between gap-2">
          <h1
            id="how-title"
            className={`${TITLE} text-[2.75rem] leading-[1.04] lg:text-[clamp(3.5rem,6vw,6rem)]`}
          >
            {t("title")}
          </h1>
          <SpeakButton text={t("title")} />
        </div>
        <p className="text-lead max-w-[46ch]">{t("line")}</p>
        <nav aria-label={t("jump")} className="flex flex-wrap gap-x-6 font-semibold">
          <a href="#comptes" className="inline-flex min-h-12 items-center underline">
            {t("accounts.title")}
          </a>
          {JOURNEYS.map(({ key, id }) => (
            <a key={key} href={`#${id}`} className="inline-flex min-h-12 items-center underline">
              {t(`${key}.short`)}
            </a>
          ))}
          <a href="#audio" className="inline-flex min-h-12 items-center underline">
            {t("audio.short")}
          </a>
        </nav>
      </EditorialSection>

      <EditorialSection
        id="comptes"
        aria-labelledby="accounts-title"
        className="scroll-mt-4 px-4 py-14 lg:px-10 lg:py-24"
      >
        <h2
          id="accounts-title"
          className={`${TITLE} text-[2.5rem] leading-[1.06] lg:text-[4.5rem]`}
        >
          {t("accounts.title")}
        </h2>
        <p className="text-lead mt-4 max-w-[52ch]">{t("accounts.line")}</p>
        <ul className="border-trait mt-8 border-t">
          {ACCOUNTS.map((kind) => (
            <li
              key={kind}
              className="border-trait grid gap-3 border-b py-6 lg:grid-cols-[1fr_2fr_1.2fr] lg:gap-10"
            >
              <h3 className="font-display text-title">{t(`accounts.${kind}.title`)}</h3>
              <p>
                <span className="block font-semibold">{t("accounts.can")}</span>
                {t(`accounts.${kind}.can`)}
              </p>
              <p className="text-prune-doux">
                <span className="block font-semibold">{t("accounts.cannot")}</span>
                {t(`accounts.${kind}.cannot`)}
              </p>
            </li>
          ))}
        </ul>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/auth?as=client">{tNav("createAccount")}</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/proposer-mes-services">{tNav("iAmPro")}</Link>
          </Button>
        </div>
      </EditorialSection>

      <EditorialSection
        ambiance="poudre"
        aria-labelledby="signup-title"
        className="px-4 py-14 lg:px-10 lg:py-24"
      >
        <h2 id="signup-title" className={`${TITLE} text-[2.25rem] leading-[1.08] lg:text-[3.5rem]`}>
          {t("signup.title")}
        </h2>
        <ol className="mt-8 grid gap-6 lg:grid-cols-3 lg:gap-12">
          {lines(t, "signup.steps").map((step, index) => (
            <li key={step} className="flex gap-4">
              <span aria-hidden className="font-display text-headline text-hibiscus leading-none">
                {index + 1}
              </span>
              <span className="text-lead">{step}</span>
            </li>
          ))}
        </ol>
        <p className="text-prune-doux mt-8 max-w-[60ch]">{t("signup.note")}</p>
      </EditorialSection>

      {JOURNEYS.map(({ key, id, href }, index) => (
        <EditorialSection
          key={key}
          id={id}
          ambiance={index === 1 ? "nuit" : "jour"}
          aria-labelledby={`${id}-title`}
          className="border-trait scroll-mt-4 border-t px-4 py-14 lg:px-10 lg:py-24"
        >
          <div className="flex items-start justify-between gap-2">
            <h2
              id={`${id}-title`}
              className={`${TITLE} text-[2.25rem] leading-[1.08] lg:text-[3.5rem]`}
            >
              {t(`${key}.title`)}
            </h2>
            <SpeakButton text={t(`${key}.title`)} />
          </div>
          <ol className="mt-8 grid gap-6 lg:grid-cols-2 lg:gap-x-16">
            {lines(t, `${key}.steps`).map((step, step_index) => (
              <li key={step} className="flex gap-4">
                <span aria-hidden className="font-display text-headline leading-none">
                  {step_index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <Button asChild variant="secondary" className="mt-8">
            <Link href={href}>{t(`${key}.cta`)}</Link>
          </Button>
        </EditorialSection>
      ))}

      <EditorialSection
        id="audio"
        ambiance="poudre"
        aria-labelledby="audio-title"
        className="scroll-mt-4 px-4 py-14 lg:px-10 lg:py-24"
      >
        <h2 id="audio-title" className={`${TITLE} text-[2.25rem] leading-[1.08] lg:text-[3.5rem]`}>
          {t("audio.title")}
        </h2>
        <ul className="mt-8 flex max-w-[60ch] flex-col gap-3">
          {lines(t, "audio.items").map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </EditorialSection>
    </MarketingPage>
  );
}
