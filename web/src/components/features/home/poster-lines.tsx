import { useTranslations } from "next-intl";

import { TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";

const LINES = [
  { key: "shops", href: "/comment-ca-marche#payer" },
  { key: "selection", href: "/selection" },
  { key: "academy", href: "/academie" },
  { key: "lives", href: "/academie/lives" },
  { key: "gift", href: "/offrir" },
  { key: "talk", href: "/comment-ca-marche#comptes" },
  { key: "games", href: "/classements" },
  { key: "listen", href: "/comment-ca-marche#audio" },
] as const;

/** Everything else the platform does, as a poster: one big word per line, one short sentence. */
export function PosterLines() {
  const t = useTranslations("landing.more");
  return (
    <EditorialSection
      ambiance="rouge"
      aria-labelledby="more-title"
      className="px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <h2 id="more-title" className={`${TITLE} text-headline xl:text-display`}>
        {t("title")}
      </h2>
      <ul className="mt-8 flex flex-col">
        {LINES.map(({ key, href }) => (
          <li key={key} className="sg-rise">
            <Link
              href={href}
              className="press group flex flex-col gap-1 py-3 xl:grid xl:grid-cols-[minmax(0,8fr)_minmax(0,4fr)] xl:items-baseline xl:gap-8 xl:py-1"
            >
              <span className="font-display text-[clamp(2.75rem,12vw,4rem)] leading-none group-hover:underline group-hover:decoration-[0.06em] group-hover:underline-offset-[0.1em] xl:text-[clamp(4.5rem,8vw,8.5rem)] xl:leading-[0.98]">
                {t(`${key}.name`)}
              </span>
              <span>{t(`${key}.text`)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </EditorialSection>
  );
}
