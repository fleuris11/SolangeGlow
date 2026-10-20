import {
  Bell,
  CalendarCheck,
  Clock,
  Lightning,
  User,
  UsersThree,
} from "@phosphor-icons/react/dist/ssr";
import type { CSSProperties } from "react";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { BookingFlow } from "@/components/features/booking/booking-flow";
import { EmbedHeight } from "@/components/features/glowpro/embed-height";
import { bookingOnServer, widgetOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamic = "force-dynamic";

const SLUG = /^[a-z0-9-]{3,40}$/i;

/** Readable text on the salon's colour: white on dark colours, plum on light ones. */
function textOn(hex: string): string {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255) as [
    number,
    number,
    number,
  ];
  const linear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const luminance = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
  return luminance > 0.4 ? "var(--sur-couleur-claire)" : "var(--sur-couleur-sombre)";
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "glowpro.embed" });
  return { title: t("title"), robots: { index: false, follow: false } };
}

export default async function EmbedPage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "glowpro.embed" });
  const widget = SLUG.test(slug) ? await widgetOnServer(slug.toLowerCase(), locale) : null;
  const page = widget ? await bookingOnServer(widget.slug, locale) : null;
  if (!widget || !page) {
    return <p className="text-prune-doux p-4">{t("unavailable")}</p>;
  }
  const icon = { "aria-hidden": true, size: 22 } as const;
  const style = {
    "--hibiscus": widget.color,
    "--hibiscus-press": widget.color,
    "--sur-hibiscus": textOn(widget.color),
  } as CSSProperties;
  return (
    <div style={style} className="flex flex-col gap-4">
      <h1 className="text-headline font-bold">{t("heading", { name: widget.name })}</h1>
      <BookingFlow
        page={page}
        slug={widget.slug}
        embedded
        icons={{
          clock: <Clock {...icon} size={18} />,
          person: <User {...icon} weight="duotone" />,
          calendar: <CalendarCheck {...icon} size={26} weight="bold" />,
          bell: <Bell {...icon} weight="bold" />,
          group: <UsersThree {...icon} weight="duotone" />,
          lightning: <Lightning {...icon} size={16} weight="fill" />,
        }}
      />
      <p className="text-small text-prune-doux">{t("poweredBy")}</p>
      <EmbedHeight />
    </div>
  );
}
