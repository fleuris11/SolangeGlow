import { useTranslations } from "next-intl";
import Image from "next/image";

import { TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

const MEDIA = library as Record<string, { src: string; color?: string }>;

/** Every skin and every hair, women and men: the platform speaks to everyone, and shows it. */
const PORTRAITS = [
  { photo: "albinism-braids", trade: "braids", focus: "50% 30%" },
  { photo: "barber-comb", trade: "hair", focus: "60% 35%" },
  { photo: "makeup-red-hair", trade: "makeup", focus: "62% 40%" },
  { photo: "vitiligo-hands", trade: "nails", focus: "50% 45%" },
  { photo: "barber-smile", trade: "hair", focus: "62% 40%" },
  { photo: "hero-afro-profile", trade: "hair", focus: "50% 12%" },
  { photo: "beard-shave", trade: "hair", focus: "60% 40%" },
  { photo: "bride-flowers", trade: "makeup", focus: "70% 45%" },
  { photo: "albinism-cornrows-man", trade: "braids", focus: "50% 25%" },
  { photo: "makeup-mirror", trade: "makeup", focus: "50% 30%" },
  { photo: "haircut-grey", trade: "hair", focus: "45% 40%" },
  { photo: "vitiligo-lips", trade: "makeup", focus: "50% 30%" },
  { photo: "bride-makeup-gold", trade: "makeup", focus: "62% 35%" },
  { photo: "barber-dryer", trade: "hair", focus: "55% 40%" },
  { photo: "hair-colour-foils", trade: "hair", focus: "50% 40%" },
] as const;

function Portraits({ copy = false }: { copy?: boolean }) {
  const t = useTranslations("landing.everyone");
  const tTrades = useTranslations("trades");
  return (
    <ul
      // The copy only makes the loop seamless: hidden from screen readers and from the keyboard.
      aria-hidden={copy || undefined}
      inert={copy || undefined}
      aria-label={copy ? undefined : t("label")}
      className={`flex shrink-0 gap-2 pr-2 xl:gap-3 xl:pr-3 ${copy ? "sg-marquee-copy" : ""}`}
    >
      {PORTRAITS.map(({ photo, trade, focus }) => (
        <li key={photo} className="w-[58vw] max-w-64 shrink-0 md:w-[30vw] xl:w-[18vw] xl:max-w-80">
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
                alt={copy ? "" : t(`alt.${photo}`)}
                fill
                loading="lazy"
                sizes="(min-width: 1280px) 18vw, (min-width: 768px) 30vw, 58vw"
                className="object-cover transition-transform duration-500 ease-[var(--courbe-sortie)] group-hover:scale-[1.03] motion-reduce:transition-none"
                style={{ objectPosition: focus }}
              />
            </div>
            <span className="text-small font-semibold">{tTrades(trade)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function EverySkin() {
  const t = useTranslations("landing.everyone");
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
      {/* The portraits slide sideways by themselves; they stop under the finger, the mouse or the
          keyboard, and with fewer animations the band is simply scrolled by hand. */}
      <div className="sg-marquee mt-10 [scrollbar-width:none] overflow-x-auto pb-4 xl:mt-14">
        <div className="sg-marquee-track sg-portraits-track flex w-max">
          <Portraits />
          <Portraits copy />
        </div>
      </div>
    </EditorialSection>
  );
}
