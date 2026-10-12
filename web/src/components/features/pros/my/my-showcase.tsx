"use client";

import {
  CaretRight,
  ChatCenteredText,
  Clock,
  Eye,
  IdentificationCard,
  Images,
  MapPin,
  QrCode,
  Rocket,
  Scissors,
  Star,
  UserCircle,
  WarningCircle,
} from "@phosphor-icons/react";
import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, type ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { publishMyPro, unpublishMyPro, type MyPro } from "@/lib/api/pros";
import { useMe } from "@/lib/auth/use-me";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { useMyPro, useSetMyPro } from "@/lib/pros/use-my-pro";

import { SECTIONS, type Section } from "./sections";

/** Which section completes each missing item of the publication checklist. */
const MISSING_SECTION: Record<string, Section> = {
  business_name: "info",
  slug: "info",
  trades: "info",
  city: "place",
  location: "place",
  where: "place",
  services: "services",
};

const ICONS: Record<Section, ReactNode> = {
  info: <UserCircle size={28} weight="duotone" />,
  services: <Scissors size={28} weight="duotone" />,
  hours: <Clock size={28} weight="duotone" />,
  portfolio: <Images size={28} weight="duotone" />,
  reviews: <Star size={28} weight="duotone" />,
  messages: <ChatCenteredText size={28} weight="duotone" />,
  place: <MapPin size={28} weight="duotone" />,
  share: <QrCode size={28} weight="duotone" />,
  verification: <IdentificationCard size={28} weight="duotone" />,
};

type Say = (key: string, values?: Record<string, string | number>) => string;

function summary(pro: MyPro, section: Section, t: Say) {
  switch (section) {
    case "services":
      return t("summary.services", { count: pro.services.length });
    case "hours":
      return pro.hours.length ? t("summary.hoursSet") : t("summary.hoursMissing");
    case "portfolio":
      return t("summary.portfolio", { count: pro.portfolio.length });
    case "reviews":
      return t("summary.reviews", { count: pro.rating_count });
    case "messages":
      return t("summary.messages");
    case "place":
      return [pro.place.district, pro.place.city].filter(Boolean).join(", ") || t("summary.empty");
    case "share":
      return pro.short_link.replace(/^https?:\/\//, "");
    case "verification":
      return t(`verification.state.${pro.verification.status}`);
    default:
      return pro.business_name || t("summary.empty");
  }
}

/** « Ma vitrine »: publish, see what is missing, open each part to edit it. */
export function MyShowcase() {
  const t = useTranslations("pros.my");
  const toast = useToast();
  const router = useRouter();
  const me = useMe();
  const pro = useMyPro();
  const setPro = useSetMyPro();

  useEffect(() => {
    if (me.data === null) router.replace("/auth");
    else if (pro.data === null) router.replace("/pro/start");
  }, [me.data, pro.data, router]);

  const publish = useMutation({
    mutationFn: (online: boolean) => (online ? publishMyPro() : unpublishMyPro()),
    onSuccess: (data, online) => {
      setPro(data);
      toast(online ? t("published") : t("unpublished"), "success");
    },
    onError: (error) => {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    },
  });

  if (!pro.data) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4">
        <Skeleton className="h-10 w-2/3 rounded-full" />
        <Skeleton className="rounded-card h-32" />
        <Skeleton className="rounded-card h-64" />
      </div>
    );
  }

  const data = pro.data;
  const missing = data.missing;
  const published = data.status === "published";
  const suspended = data.status === "suspended";

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-2">
            <h1 className="text-headline font-bold">{t("title")}</h1>
            <p className="text-lead">{data.business_name}</p>
          </div>
          <SpeakButton text={`${t("title")}. ${t(`status.${data.status}`)}`} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`text-mention rounded-full px-3 py-1 font-bold ${
              published
                ? "bg-feuille text-lait"
                : suspended
                  ? "bg-alerte text-lait"
                  : "bg-poudre text-prune"
            }`}
          >
            {t(`status.${data.status}`)}
          </span>
          {data.verified && <Badge tone="verified">{t("verifiedBadge")}</Badge>}
        </div>
        {data.slug && (
          <Link href={`/${data.slug}`} className={buttonClasses({ variant: "secondary" })}>
            <Eye aria-hidden size={22} weight="bold" />
            {published ? t("see") : t("preview")}
          </Link>
        )}
      </header>

      {suspended && (
        <div role="alert" className="border-alerte rounded-card flex gap-3 border-2 p-4">
          <WarningCircle aria-hidden size={28} weight="fill" className="text-alerte shrink-0" />
          <div>
            <p className="font-bold">{t("suspendedTitle")}</p>
            {data.suspension_reason && <p>{data.suspension_reason}</p>}
            <p className="text-small text-prune-doux">{t("suspendedText")}</p>
          </div>
        </div>
      )}

      {!published && !suspended && (
        <section
          aria-labelledby="publish-title"
          className="bg-poudre rounded-card flex flex-col gap-3 p-5"
        >
          <h2 id="publish-title" className="text-title font-bold">
            {missing.length ? t("missingTitle") : t("readyTitle")}
          </h2>
          {missing.length > 0 ? (
            <ul className="flex flex-col gap-2">
              {missing.map((code) => (
                <li key={code}>
                  <Link
                    href={`/pro/${MISSING_SECTION[code] ?? "info"}`}
                    className="text-hibiscus inline-flex min-h-12 items-center gap-2 font-bold underline"
                  >
                    <WarningCircle aria-hidden size={20} />
                    {(t as unknown as Say)(`missing.${code}`)}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p>{t("readyText")}</p>
          )}
          <Button
            size="lg"
            fullWidth
            disabled={missing.length > 0 || publish.isPending}
            onClick={() => publish.mutate(true)}
          >
            <Rocket aria-hidden size={26} weight="bold" />
            {t("publish")}
          </Button>
        </section>
      )}

      <nav aria-label={t("sectionsLabel")}>
        <ul className="flex flex-col gap-2">
          {SECTIONS.map((section) => (
            <li key={section}>
              <Link
                href={`/pro/${section}`}
                className="border-trait bg-carte rounded-card hover:border-prune-doux flex min-h-16 items-center gap-4 border p-4"
              >
                <span aria-hidden className="text-hibiscus">
                  {ICONS[section]}
                </span>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="font-bold">{t(`sections.${section}`)}</span>
                  <span className="text-small text-prune-doux truncate">
                    {summary(data, section, t as unknown as Say)}
                  </span>
                </span>
                <CaretRight aria-hidden size={20} />
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {published && (
        <Button variant="quiet" disabled={publish.isPending} onClick={() => publish.mutate(false)}>
          {t("unpublish")}
        </Button>
      )}
    </div>
  );
}
