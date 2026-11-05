import { useTranslations } from "next-intl";
import Image from "next/image";

import { TITLE } from "@/components/features/marketing/chrome";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";

const LEVELS = [
  { left: "agenda", right: "slots" },
  { left: "places", right: "page" },
  { left: "shop", right: "lives" },
] as const;

type NoteName = "agenda" | "slots" | "places" | "page" | "shop" | "lives";

const CHAPTER_OF: Record<NoteName, string> = {
  agenda: "agenda",
  slots: "agenda",
  places: "agenda",
  page: "page",
  shop: "shop",
  lives: "academy",
};

function Note({ name, side }: { name: NoteName; side: "left" | "right" }) {
  const t = useTranslations("landing.plate.notes");
  return (
    <Link
      href={`/proposer-mes-services#${CHAPTER_OF[name]}`}
      data-note={name}
      className={`sg-rise block self-start xl:max-w-[24ch] ${
        side === "left" ? "xl:justify-self-end xl:text-right" : ""
      }`}
    >
      <span className="text-lead block font-semibold">{t(`${name}.title`)}</span>
      <span className="text-small mt-1 block">{t(`${name}.text`)}</span>
    </Link>
  );
}

function Slice({ level }: { level: 0 | 1 | 2 }) {
  const t = useTranslations("landing.plate.ui");
  const round = level === 0 ? "rounded-t-card" : level === 2 ? "rounded-b-card" : "";
  return (
    <div
      data-ui
      data-ambiance="papier"
      role="img"
      aria-label={t(`labels.l${level}`)}
      className={`bg-poudre! flex flex-col gap-3 p-4 max-xl:col-span-2 xl:col-start-2 ${round}`}
    >
      {level === 0 && (
        <>
          <div data-part="agenda" className="flex flex-col gap-2">
            <p className="font-display text-title">{t("today")}</p>
            <div className="bg-blanc rounded-field flex items-center gap-3 p-3">
              <span className="font-semibold tabular-nums">{t("a1.time")}</span>
              <span className="min-w-0 flex-1 truncate">{t("a1.who")}</span>
              <span className="text-small text-feuille font-semibold">{t("a1.state")}</span>
            </div>
            <div className="bg-blanc rounded-field flex items-center gap-3 p-3">
              <span className="font-semibold tabular-nums">{t("a2.time")}</span>
              <span className="min-w-0 flex-1 truncate">{t("a2.who")}</span>
              <span className="bg-rouge text-sur-hibiscus rounded-button text-small px-2 py-1 font-semibold">
                {t("a2.state")}
              </span>
            </div>
          </div>
          <div data-part="slots">
            <p className="text-small mb-1 font-semibold">{t("slots")}</p>
            <div className="grid grid-cols-3 gap-1.5">
              {(["s1", "s2", "s3"] as const).map((slot) => (
                <span
                  key={slot}
                  className="bg-blanc rounded-button text-small flex min-h-10 items-center justify-center font-semibold tabular-nums"
                >
                  {t(slot)}
                </span>
              ))}
            </div>
          </div>
        </>
      )}
      {level === 1 && (
        <>
          <div data-part="places">
            <p className="text-small mb-1 font-semibold">{t("places")}</p>
            <div className="bg-blanc rounded-field flex flex-col gap-1 p-3">
              <span className="flex justify-between gap-2">
                <span>{t("place1")}</span>
                <span className="text-prune-doux text-small">{t("place1Meta")}</span>
              </span>
              <span className="flex justify-between gap-2">
                <span>{t("place2")}</span>
                <span className="text-prune-doux text-small">{t("place2Meta")}</span>
              </span>
            </div>
          </div>
          <div data-part="page" className="bg-blanc rounded-field flex items-center gap-3 p-3">
            <Image
              src="/brand/qr-exemple.svg"
              alt=""
              width={56}
              height={56}
              unoptimized
              loading="lazy"
              className="size-14 shrink-0"
            />
            <span className="min-w-0">
              <span className="block font-semibold">{t("page")}</span>
              <span className="text-small text-prune-doux block [overflow-wrap:anywhere]">
                solangeglow.com/aicha
              </span>
            </span>
          </div>
        </>
      )}
      {level === 2 && (
        <>
          <div
            data-part="shop"
            className="bg-blanc rounded-field flex items-center justify-between gap-3 p-3"
          >
            <span className="font-semibold">{t("shop")}</span>
            <span className="text-small text-prune-doux">{t("shopMeta")}</span>
          </div>
          <div
            data-part="lives"
            className="bg-encre text-blanc rounded-button flex min-h-12 items-center justify-center font-semibold"
          >
            {t("live")}
          </div>
        </>
      )}
    </div>
  );
}

/** The space of someone who offers services, shown whole like a plate, each part explained. */
export function ActivityPlate() {
  const t = useTranslations("landing.plate");
  return (
    <EditorialSection
      aria-labelledby="plate-title"
      className="sg-plate px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <h2 id="plate-title" className={`${TITLE} text-headline xl:text-display max-w-[18ch]`}>
        {t("title")}
      </h2>
      <p className="mt-2 max-w-[42ch]">{t("line")}</p>
      <div className="mt-10 grid grid-cols-2 gap-x-4 max-xl:gap-y-4 xl:mx-auto xl:max-w-[76rem] xl:grid-cols-[1fr_25rem_1fr] xl:gap-x-12">
        {LEVELS.map(({ left, right }, level) => (
          <div
            key={left}
            className="col-span-2 grid grid-cols-subgrid gap-y-4 xl:col-span-3 xl:gap-y-0"
          >
            <Slice level={level as 0 | 1 | 2} />
            <div className="xl:col-start-1 xl:row-start-1 xl:flex xl:justify-end xl:pt-6">
              <Note name={left} side="left" />
            </div>
            <div className="xl:col-start-3 xl:row-start-1 xl:pt-6">
              <Note name={right} side="right" />
            </div>
          </div>
        ))}
      </div>
      <Button asChild size="lg" className="mt-10 max-sm:w-full">
        <Link href="/proposer-mes-services">{t("cta")}</Link>
      </Button>
    </EditorialSection>
  );
}
