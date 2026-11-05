import { useTranslations } from "next-intl";
import Image from "next/image";

import { TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

import { StepsWatcher } from "./steps-watcher";

const MEDIA = library as Record<string, { src: string }>;
const STEPS = ["choose", "book", "show"] as const;
const TALENTS = [
  { key: "a", photo: "braids-hoops" },
  { key: "b", photo: "cornrows-glasses" },
  { key: "c", photo: "locs-beauty" },
] as const;
const SLOTS = ["s1", "s2", "s3", "s4", "s5", "s6"] as const;

/** A piece of the real product, at its real size, in one of its three states. */
function FragmentState({ index }: { index: number }) {
  const t = useTranslations("landing.steps.ui");
  if (index === 0) {
    return (
      <>
        <p className="font-display text-title">{t("resultsTitle")}</p>
        <p className="text-small text-prune-doux">{t("resultsLine")}</p>
        <ul className="mt-3 flex flex-col gap-3">
          {TALENTS.map(({ key, photo }, row) => (
            <li
              key={key}
              className={`rounded-card flex items-center gap-3 p-2 ${row === 0 ? "bg-poudre" : ""}`}
            >
              <span className="relative size-14 shrink-0 overflow-clip rounded-full">
                <Image
                  src={MEDIA[photo]!.src}
                  alt=""
                  fill
                  loading="lazy"
                  sizes="56px"
                  className="object-cover"
                />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{t(`talents.${key}.name`)}</span>
                <span className="text-small text-prune-doux block">{t(`talents.${key}.meta`)}</span>
              </span>
              <span className="text-small shrink-0 font-semibold tabular-nums">
                {t(`talents.${key}.price`)}
              </span>
            </li>
          ))}
        </ul>
      </>
    );
  }
  if (index === 1) {
    return (
      <>
        <p className="font-display text-title">{t("talents.a.name")}</p>
        <p className="text-small text-prune-doux">{t("service")}</p>
        <p className="mt-4 font-semibold">{t("day")}</p>
        <ul className="mt-2 grid grid-cols-3 gap-1.5">
          {SLOTS.map((slot) => (
            <li
              key={slot}
              className={`rounded-button text-small flex min-h-11 items-center justify-center font-semibold tabular-nums ${
                slot === "s3" ? "bg-encre text-blanc" : "bg-poudre"
              }`}
            >
              {t(`slots.${slot}`)}
            </li>
          ))}
        </ul>
        <p className="bg-rouge text-sur-hibiscus rounded-button mt-5 flex min-h-12 items-center justify-center px-3 text-center font-semibold">
          {t("bookCta")}
        </p>
        <p className="text-small text-prune-doux mt-3 text-center">{t("reminder")}</p>
      </>
    );
  }
  return (
    <div className="text-center">
      <p className="font-display text-title">{t("confirmed")}</p>
      <p className="font-semibold">{t("talents.a.name")}</p>
      <p className="text-small text-prune-doux">{t("whenLine")}</p>
      <Image
        src="/brand/qr/braids.svg"
        alt=""
        width={192}
        height={192}
        unoptimized
        loading="lazy"
        className="mx-auto mt-3 size-48"
      />
      <p className="text-small mt-2">{t("showLine")}</p>
    </div>
  );
}

function Paper({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div
      data-ui
      data-ambiance="papier"
      role="img"
      aria-label={label}
      className="rounded-card w-full max-w-[24rem] p-4"
    >
      {children}
    </div>
  );
}

/**
 * Three sentences. On a computer one piece of the product stays in view and changes under them; on a
 * phone each sentence simply has its own state, so nothing ever covers the text.
 */
export function Steps() {
  const t = useTranslations("landing.steps");
  const label = t("ui.label");
  return (
    <EditorialSection
      id="etapes"
      aria-labelledby="steps-title"
      data-active="0"
      className="sg-steps px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <div className="xl:grid xl:grid-cols-12 xl:gap-x-16">
        <div className="xl:col-span-5">
          <h2 id="steps-title" className={`${TITLE} text-headline xl:text-display`}>
            {t("title")}
          </h2>
          <ol className="mt-8 flex flex-col gap-10 xl:mt-0 xl:gap-0">
            {STEPS.map((step, index) => (
              <li
                key={step}
                data-step={index}
                className="flex flex-col gap-4 xl:min-h-[62vh] xl:justify-center"
              >
                <div className="flex flex-col gap-1">
                  <p className={`${TITLE} text-title xl:text-headline`}>{t(`${step}.title`)}</p>
                  <p className="text-prune max-w-[36ch]">{t(`${step}.text`)}</p>
                </div>
                <div className="bg-poudre rounded-card flex justify-center p-3 md:p-6 xl:hidden">
                  <Paper label={label}>
                    <FragmentState index={index} />
                  </Paper>
                </div>
              </li>
            ))}
          </ol>
        </div>
        <div className="bg-poudre rounded-card sticky top-[12vh] hidden h-[76vh] items-center justify-center self-start p-8 xl:col-span-7 xl:flex">
          <Paper label={label}>
            {STEPS.map((step, index) => (
              <div key={step} data-state={index}>
                <FragmentState index={index} />
              </div>
            ))}
          </Paper>
        </div>
      </div>
      <Link
        href="/comment-ca-marche"
        className="mt-6 inline-flex min-h-12 items-center font-semibold underline underline-offset-4"
      >
        {t("more")}
      </Link>
      <StepsWatcher target="etapes" />
    </EditorialSection>
  );
}
