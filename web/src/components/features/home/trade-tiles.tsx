import { useTranslations } from "next-intl";
import Image from "next/image";

import { lines, TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

const MEDIA = library as Record<string, { src: string; poster?: string }>;

/** Each print has a tag tied to it. The pairs of colours make a plain grid look alive. */
const TILES = [
  { key: "braids", photo: "braids-lilac", tag: "bg-nuit text-blanc" },
  { key: "hair", photo: "curls-teal", tag: "bg-rouge-fixe text-blanc" },
  { key: "makeup", photo: "lips-orange", tag: "bg-poudre-fixe text-encre" },
  { key: "nails", photo: "nails-pro", tag: "bg-nuit text-blanc" },
  { key: "sewing", photo: "wax-rolls", tag: "bg-poudre-fixe text-encre" },
  { key: "headwrap", photo: "headwrap-mural", tag: "bg-nuit text-blanc" },
  { key: "skincare", photo: "skin-profile", tag: "bg-rouge-fixe text-blanc" },
  { key: "all", photo: "video-makeup-set", tag: "bg-nuit text-blanc" },
] as const;

/* Written into the page, no JavaScript file (ADR-004). Nothing is downloaded in data saver or with
   fewer animations: the picture underneath stays. */
const PLAY = `(function(){var v=document.getElementById("sg-tile-video"),h=document.documentElement;
if(!v||h.dataset.dataSaver==="true"||h.dataset.motion==="reduced"||matchMedia("(prefers-reduced-motion: reduce)").matches)return;
v.src=v.dataset.src;v.play().catch(function(){})})()`;

export function TradeTiles() {
  const t = useTranslations("landing.tiles");
  return (
    <EditorialSection
      aria-labelledby="tiles-title"
      className="px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <h2 id="tiles-title" className={`${TITLE} text-headline xl:text-display`}>
        {t("title")}
      </h2>
      <ul className="mt-8 grid grid-cols-2 gap-2 lg:grid-cols-4 lg:gap-3">
        {TILES.map(({ key, photo, tag }, index) => {
          const video = key === "all";
          return (
            <li key={key} className="sg-rise" style={{ "--i": index % 4 } as React.CSSProperties}>
              <Link
                href={key === "all" ? "/explore" : { pathname: "/explore", query: { trade: key } }}
                className="press sg-tile block h-full"
              >
                <div className="bg-poudre relative aspect-[4/5] overflow-clip">
                  <Image
                    src={video ? MEDIA[photo]!.poster! : MEDIA[photo]!.src}
                    alt={t(`${key}.alt`)}
                    fill
                    loading="lazy"
                    unoptimized={video}
                    sizes="(min-width: 1024px) 25vw, 50vw"
                    className="object-cover"
                  />
                  {video && (
                    <video
                      id="sg-tile-video"
                      data-src={MEDIA[photo]!.src}
                      poster={MEDIA[photo]!.poster}
                      muted
                      loop
                      playsInline
                      preload="none"
                      aria-hidden
                      className="absolute inset-0 size-full object-cover"
                    />
                  )}
                </div>
                <div className={`flex min-h-24 flex-col gap-1 p-3 ${tag}`}>
                  <span className="font-display text-title leading-none">{t(`${key}.name`)}</span>
                  <span className="text-mention flex flex-wrap justify-between gap-x-3 font-semibold">
                    {lines(t, `${key}.subs`).map((sub) => (
                      <span key={sub}>{sub}</span>
                    ))}
                  </span>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
      <script dangerouslySetInnerHTML={{ __html: PLAY }} />
    </EditorialSection>
  );
}
