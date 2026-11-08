import { Check } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import Image from "next/image";

import { TITLE } from "@/components/features/marketing/chrome";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

const MEDIA = library as Record<string, { src: string }>;
const POINTS = ["a", "b", "c", "d"] as const;
const SLOTS = ["a", "b", "c", "d"] as const;

/**
 * For the professionals: what is free (showcase, agenda, clients) and that Solange Glow brings them
 * clients. The product itself is the picture: a computer with the agenda, a phone with the showcase,
 * turned a little in space and straightened as the visitor scrolls.
 */
export function ProFree() {
  const t = useTranslations("landing.proFree");
  return (
    <EditorialSection
      ambiance="rouge"
      aria-labelledby="pro-free-title"
      className="grid gap-12 overflow-clip px-4 py-16 md:px-8 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] xl:items-center xl:px-10 xl:py-24"
    >
      <div className="flex flex-col gap-6">
        <h2 id="pro-free-title" className={`${TITLE} text-headline xl:text-display`}>
          <span className="block">{t("first")}</span>
          <span className="block">{t("second")}</span>
        </h2>
        <p className="text-lead max-w-[34rem]">{t("line")}</p>
        <ul className="flex flex-col gap-3">
          {POINTS.map((key) => (
            <li key={key} className="flex items-start gap-3 font-semibold">
              <Check aria-hidden size={24} weight="bold" className="mt-0.5 shrink-0" />
              {t(`points.${key}`)}
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="primary" size="lg">
            <Link href="/proposer-mes-services">{t("cta")}</Link>
          </Button>
          <Button asChild variant="secondary" size="lg">
            <Link href="/auth?as=pro">{t("start")}</Link>
          </Button>
        </div>
      </div>

      <div
        data-ui
        aria-label={t("ui.label")}
        role="img"
        className="sg-devices relative mx-auto w-full max-w-[40rem]"
      >
        {/* The computer: the day of the agenda. */}
        <div className="sg-device-laptop bg-encre w-[88%] rounded-[1.25rem] p-2 sm:p-3">
          <div className="bg-blanc text-encre overflow-clip rounded-xl p-4">
            <p className="font-display text-title">{t("ui.day")}</p>
            <ul className="mt-3 grid gap-2">
              {SLOTS.map((key, index) => (
                <li
                  key={key}
                  className={`flex items-center justify-between gap-3 rounded-lg px-3 py-2 ${
                    index === 1 ? "bg-rouge-fixe text-blanc" : "bg-poudre-fixe"
                  }`}
                >
                  <span className="font-semibold tabular-nums">{t(`ui.slots.${key}.time`)}</span>
                  <span className="text-small min-w-0 flex-1 truncate">
                    {t(`ui.slots.${key}.what`)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        {/* The phone: the showcase a client opens from the QR code. */}
        <div className="sg-device-phone bg-encre absolute -right-1 -bottom-10 w-[40%] max-w-52 rounded-[1.75rem] p-1.5 sm:-right-4">
          <div className="bg-blanc text-encre overflow-clip rounded-[1.4rem]">
            <div className="relative aspect-[4/5]">
              <Image
                src={MEDIA["braids-hoops"]!.src}
                alt=""
                fill
                loading="lazy"
                sizes="200px"
                className="object-cover"
              />
            </div>
            <div className="flex flex-col gap-1 p-3">
              <span className="text-small font-semibold">{t("ui.name")}</span>
              <span className="text-mention">{t("ui.open")}</span>
              <span className="bg-rouge-fixe text-blanc text-mention mt-1 rounded-full py-1.5 text-center font-semibold">
                {t("ui.book")}
              </span>
            </div>
          </div>
        </div>
      </div>
    </EditorialSection>
  );
}
