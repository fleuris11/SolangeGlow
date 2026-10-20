import {
  ArrowLeft,
  BellRinging,
  CalendarCheck,
  Clock,
  Lightning,
  MapPin,
  User,
  UsersThree,
} from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { cache } from "react";

import { BookingFlow } from "@/components/features/booking/booking-flow";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { bookingOnServer, SITE_URL } from "@/lib/api/server";
import { Link } from "@/lib/i18n/navigation";
import type { Locale } from "@/lib/i18n/routing";
import { mediaSrc } from "@/lib/media";

type Props = {
  params: Promise<{ locale: Locale; slug: string }>;
  searchParams: Promise<{ service?: string; post?: string }>;
};

// Rendered on the server at each visit: services and rules are always fresh.
export const dynamic = "force-dynamic";

const SLUG = /^[a-z0-9-]{3,40}$/i;
const ID = /^[0-9a-f-]{36}$/i;
const loadPage = cache((slug: string, locale: string) =>
  SLUG.test(slug) ? bookingOnServer(slug.toLowerCase(), locale) : null,
);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = await loadPage(slug, locale);
  if (!page) return {};
  const t = await getTranslations({ locale, namespace: "booking.page" });
  return {
    title: t("title", { name: page.pro.name }),
    description: t("metaDescription", { name: page.pro.name, city: page.pro.city }),
    alternates: { canonical: `${SITE_URL}/${locale}/${slug.toLowerCase()}/rdv` },
  };
}

export default async function BookingPage({ params, searchParams }: Props) {
  const { locale, slug } = await params;
  const { service, post } = await searchParams;
  setRequestLocale(locale);
  const page = await loadPage(slug, locale);
  if (!page) notFound();
  const t = await getTranslations({ locale, namespace: "booking.page" });
  const place = [page.pro.address, page.pro.district, page.pro.city].filter(Boolean).join(", ");
  const icon = { "aria-hidden": true, size: 22 } as const;

  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-4">
        <Link
          href={`/${page.pro.slug}`}
          className="text-prune-doux hover:bg-poudre -ml-2 inline-flex min-h-12 items-center gap-2 self-start rounded-full px-2 font-bold"
        >
          <ArrowLeft aria-hidden size={22} />
          {t("back", { name: page.pro.name })}
        </Link>
        <div className="flex items-center gap-4">
          <Avatar name={page.pro.name} src={mediaSrc(page.pro.photo, "thumb")} size="md" />
          <div className="flex min-w-0 flex-col gap-1">
            <h1 className="text-headline font-bold">{t("title", { name: page.pro.name })}</h1>
            {page.pro.is_verified && <Badge tone="verified">{t("verified")}</Badge>}
          </div>
        </div>
        {place && (
          <p className="text-prune-doux flex items-center gap-2">
            <MapPin aria-hidden size={22} />
            {place}
          </p>
        )}
        {page.last_minute?.is_active && (
          <p className="bg-poudre flex items-center gap-2 rounded-2xl p-3 font-bold">
            <Lightning aria-hidden size={24} weight="fill" className="text-hibiscus" />
            {t("lastMinute", {
              percent: page.last_minute.percent_off,
              hours: page.last_minute.window_hours,
            })}
          </p>
        )}
      </header>
      {page.services.length === 0 ? (
        <p className="text-prune-doux">{t("noService")}</p>
      ) : (
        <BookingFlow
          page={page}
          slug={page.pro.slug ?? slug}
          initialServiceId={service && ID.test(service) ? service : undefined}
          postId={post && ID.test(post) ? post : undefined}
          icons={{
            clock: <Clock {...icon} size={18} />,
            person: <User {...icon} weight="duotone" />,
            calendar: <CalendarCheck {...icon} size={26} weight="bold" />,
            bell: <BellRinging {...icon} weight="bold" />,
            group: <UsersThree {...icon} weight="duotone" />,
            lightning: <Lightning {...icon} size={16} weight="fill" />,
          }}
        />
      )}
    </article>
  );
}
