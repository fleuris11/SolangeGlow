import { useTranslations } from "next-intl";
import Image from "next/image";

import { TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

const MEDIA = library as Record<string, { src: string; color?: string }>;

/** Every skin and every hair: the platform speaks to everyone, and shows it. */
const PORTRAITS = [
  { photo: "albinism-braids", trade: "braids", focus: "50% 30%" },
  { photo: "makeup-red-hair", trade: "makeup", focus: "62% 40%" },
  { photo: "vitiligo-hands", trade: "nails", focus: "50% 45%" },
  { photo: "hero-afro-profile", trade: "hair", focus: "50% 12%" },
  { photo: "bride-makeup-gold", trade: "makeup", focus: "62% 35%" },
  { photo: "albinism-cornrows-man", trade: "braids", focus: "50% 25%" },
  { photo: "vitiligo-lips", trade: "makeup", focus: "50% 30%" },
  { photo: "hair-colour-foils", trade: "hair", focus: "50% 40%" },
] as const;

export function EverySkin() {
  const t = useTranslations("landing.everyone");
  const tTrades = useTranslations("trades");
  return (
    <EditorialSection
      ambiance="nuit"
      aria-labelledby="everyone-title"
      className="overflow-clip py-16 xl:py-24"
    >
      <div className="grid gap-4 px-4 md:px-8 xl:grid-cols-2 xl:items-end xl:gap-10 xl:px-10">
        <h2 id="everyone-title" className={`${TITLE} text-headline xl:text-display`}>
          <span className="block">{t("first")}</span>
          <span className="block">{t("second")}</span>
        </h2>
        <p className="text-lead max-w-[34rem]">{t("line")}</p>
      </div>
      <ul
        className="mt-10 flex snap-x snap-mandatory [scrollbar-width:none] gap-2 overflow-x-auto px-4 pb-4 md:px-8 xl:mt-14 xl:grid xl:grid-cols-4 xl:gap-3 xl:overflow-visible xl:px-10 xl:pb-12"
        aria-label={t("label")}
      >
        {PORTRAITS.map(({ photo, trade, focus }, index) => (
          <li
            key={photo}
            className={`sg-rise w-[64vw] max-w-72 shrink-0 snap-start md:w-[40vw] xl:w-auto xl:max-w-none ${
              index % 2 ? "xl:translate-y-12" : ""
            }`}
            style={{ "--i": index % 4 } as React.CSSProperties}
          >
            <Link
              href={{ pathname: "/explore", query: { trade } }}
              className="press group flex flex-col gap-2"
            >
              <div
                className="relative aspect-[3/4] overflow-clip"
                style={{ backgroundColor: MEDIA[photo]?.color }}
              >
                <Image
                  src={MEDIA[photo]!.src}
                  alt={t(`alt.${photo}`)}
                  fill
                  loading="lazy"
                  sizes="(min-width: 1280px) 25vw, (min-width: 768px) 40vw, 64vw"
                  className="object-cover transition-transform duration-500 ease-[var(--courbe-sortie)] group-hover:scale-[1.03] motion-reduce:transition-none"
                  style={{ objectPosition: focus }}
                />
              </div>
              <span className="text-small font-semibold">{tTrades(trade)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </EditorialSection>
  );
}
