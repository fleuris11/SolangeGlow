import { Check } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import Image from "next/image";

import { lines, TITLE } from "@/components/features/marketing/chrome";
import { Button } from "@/components/ui/button";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";
import library from "@/lib/media/library.json";

const MEDIA = library as Record<string, { src: string }>;

const SIDES = [
  { key: "seek", door: "client", photo: "curls-blue", focus: "50% 22%", href: "/auth?as=client" },
  { key: "offer", door: "pro", photo: "salon-pink", focus: "50% 30%", href: "/auth?as=pro" },
] as const;

/**
 * The one control the platform turns on: seek or offer. It is set very large, because it is what a
 * visitor must understand, and the same account really goes from one side to the other.
 */
export function TwoSides() {
  const t = useTranslations("landing.sides");
  const tWho = useTranslations("marketing.who");
  const tMarketing = useTranslations("marketing");
  return (
    <EditorialSection
      ambiance="nuit"
      aria-labelledby="sides-title"
      className="sg-sides overflow-clip px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <h2 id="sides-title" className={`${TITLE} sg-rise text-headline xl:text-display`}>
        {t("title")}
      </h2>
      <fieldset className="mt-6 min-w-0 xl:mt-8">
        <legend className="sr-only">{t("legend")}</legend>
        <div
          data-ui
          className="sg-track font-display relative isolate grid w-max auto-cols-fr grid-flow-col bg-white/15 text-[8.4vw] leading-none xl:-mr-10 xl:pr-[40vw] xl:text-[clamp(4.5rem,7vw,7.5rem)]"
        >
          <span
            aria-hidden
            className="sg-thumb bg-blanc absolute inset-y-0 left-0 -z-10 w-1/2 xl:w-[calc((100%-40vw)/2)]"
          />
          {SIDES.map(({ key }) => (
            <div key={key}>
              <input
                type="radio"
                name="home-side"
                id={`side-${key}`}
                value={key}
                defaultChecked={key === "seek"}
                className="sr-only"
              />
              <label
                htmlFor={`side-${key}`}
                data-for={key}
                className="block cursor-pointer px-[0.4em] pt-[0.36em] pb-[0.24em] whitespace-nowrap"
              >
                {t(key)}
              </label>
            </div>
          ))}
        </div>
      </fieldset>
      <p className="text-lead mt-4">{t("line")}</p>

      {SIDES.map(({ key, door, photo, focus, href }) => (
        <div key={key} data-side={key} className="mt-10 xl:mt-14">
          <div className="grid gap-8 md:grid-cols-2 xl:gap-16">
            <div className="flex flex-col gap-5">
              <h3 className={`${TITLE} text-display`}>{tWho(`${door}.title`)}</h3>
              <p className="text-lead max-w-[34ch]">{tWho(`${door}.text`)}</p>
              <ul className="flex flex-col gap-2">
                {lines(tWho, `${door}.items`).map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <Check aria-hidden size={20} weight="bold" className="mt-1 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
                <Button asChild size="lg">
                  <Link href={href}>{tWho(`${door}.cta`)}</Link>
                </Button>
                {door === "pro" && (
                  <Link
                    href="/proposer-mes-services"
                    className="inline-flex min-h-12 items-center font-semibold underline underline-offset-4"
                  >
                    {t("seeAll")}
                  </Link>
                )}
              </div>
              <p className="flex flex-wrap items-center gap-x-2">
                {tWho("already")}
                <Link
                  href="/auth"
                  className="inline-flex min-h-12 items-center font-semibold underline underline-offset-4"
                >
                  {tMarketing("signIn")}
                </Link>
              </p>
            </div>
            <div className="rounded-photo relative aspect-[4/3] overflow-clip md:aspect-auto md:min-h-[26rem]">
              <Image
                src={MEDIA[photo]!.src}
                alt={t(`alt.${key}`)}
                fill
                loading="lazy"
                sizes="(min-width: 768px) 50vw, 100vw"
                className="object-cover"
                style={{ objectPosition: focus }}
              />
            </div>
          </div>
        </div>
      ))}
    </EditorialSection>
  );
}
