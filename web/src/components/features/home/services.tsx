import {
  CalendarCheck,
  ChatsCircle,
  Gift,
  GraduationCap,
  Sparkle,
  Storefront,
  Truck,
  VideoCamera,
} from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";
import { Link } from "@/lib/i18n/navigation";

/** Everything the platform does, in one look, each with the door that opens it. */
const SERVICES = [
  { key: "book", href: "/explore", Icon: CalendarCheck },
  { key: "shops", href: "/explore", Icon: Storefront },
  { key: "selection", href: "/selection", Icon: Truck },
  { key: "academy", href: "/academie", Icon: GraduationCap },
  { key: "gifts", href: "/offrir", Icon: Gift },
  { key: "messages", href: "/messages", Icon: ChatsCircle },
  { key: "lives", href: "/academie/lives", Icon: VideoCamera },
  { key: "games", href: "/points", Icon: Sparkle },
] as const;

export function Services() {
  const t = useTranslations("landing.services");
  return (
    <EditorialSection
      id="services"
      aria-labelledby="services-title"
      className="scroll-mt-4 px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <div className="grid gap-4 xl:grid-cols-2 xl:items-end xl:gap-10">
        <h2 id="services-title" className={`${TITLE} text-headline xl:text-display`}>
          <span className="block">{t("first")}</span>
          <span className="block">{t("second")}</span>
        </h2>
        <p className="text-lead max-w-[34rem]">{t("line")}</p>
      </div>
      <ul className="sg-services mt-10 grid grid-cols-2 gap-2 sm:gap-3 xl:mt-14 xl:grid-cols-4">
        {SERVICES.map(({ key, href, Icon }, index) => (
          <li key={key} className="sg-rise" style={{ "--i": index % 4 } as React.CSSProperties}>
            <Link
              href={href}
              className="sg-service bg-poudre flex h-full flex-col gap-2 rounded-[1.25rem] p-4 sm:gap-3 xl:p-6"
            >
              <Icon aria-hidden size={32} />
              <span className="font-display text-lead xl:text-title">{t(`${key}.title`)}</span>
              <span className="text-small text-prune-doux xl:text-body">{t(`${key}.text`)}</span>
              <span className="text-small xl:text-body mt-auto pt-1 font-semibold underline underline-offset-4">
                {t(`${key}.cta`)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </EditorialSection>
  );
}
