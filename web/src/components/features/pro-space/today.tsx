"use client";

import {
  CalendarCheck,
  CalendarPlus,
  CheckCircle,
  ClockClockwise,
  Copy,
  Package,
  PauseCircle,
  Plus,
  QrCode,
  Scissors,
  ShareNetwork,
  Wallet,
  WarningCircle,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import {
  confirmAppointment,
  getAgenda,
  getAgendaSettings,
  type Appointment,
} from "@/lib/api/booking";
import { ApiError } from "@/lib/api/client";
import { getWallet } from "@/lib/api/payments";
import { getMyPro, myProQueryKey, printableUrl } from "@/lib/api/pros";
import { getOrders } from "@/lib/api/shop";
import { dayName, localDay, timeAt } from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

function Card({
  id,
  title,
  action,
  children,
}: {
  id: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      aria-labelledby={id}
      className="border-trait rounded-card flex flex-col gap-3 border p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 id={id} className="font-display text-lead">
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

/** The whole day on one line: what is taken in the red of the logo, what is free stays empty. */
function DayStrip({
  appointments,
  zone,
  locale,
  label,
}: {
  appointments: Appointment[];
  zone: string;
  locale: string;
  label: string;
}) {
  if (appointments.length === 0) return null;
  const HOUR = 3_600_000;
  const times = appointments.flatMap((a) => [Date.parse(a.starts_at), Date.parse(a.ends_at)]);
  const first = Math.floor(Math.min(...times) / HOUR) * HOUR;
  const last = Math.ceil(Math.max(...times) / HOUR) * HOUR;
  const span = Math.max(last - first, 4 * HOUR);
  const at = (time: number) => ((time - first) / span) * 100;
  return (
    <figure aria-label={label} className="flex flex-col gap-1">
      <div aria-hidden className="bg-poudre rounded-field relative h-8 overflow-clip">
        {appointments.map((a) => (
          <span
            key={a.id}
            title={`${timeAt(a.starts_at, zone, locale)} ${a.client_name}`}
            className="bg-rouge absolute inset-y-0"
            style={{
              left: `${at(Date.parse(a.starts_at))}%`,
              width: `max(0.25rem, ${at(Date.parse(a.ends_at)) - at(Date.parse(a.starts_at))}%)`,
            }}
          />
        ))}
      </div>
      <figcaption className="text-mention text-prune-doux flex justify-between tabular-nums">
        <span>{timeAt(new Date(first).toISOString(), zone, locale)}</span>
        <span>{timeAt(new Date(first + span).toISOString(), zone, locale)}</span>
      </figcaption>
    </figure>
  );
}

function link(appointment: Appointment) {
  return `/pro/agenda?day=${appointment.starts_at.slice(0, 10)}&rdv=${appointment.id}`;
}

/** The first screen of a pro: what waits for her today, and her link under the thumb. */
export function TodayScreen({ welcome }: { welcome: boolean }) {
  const t = useTranslations("proSpace.today");
  const tStatus = useTranslations("booking.status");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState<string | null>(null);
  const pro = useQuery({ queryKey: myProQueryKey, queryFn: getMyPro, retry: false });
  const agenda = useQuery({
    queryKey: ["agenda", "today"],
    queryFn: () => getAgenda({ days: 1 }),
    retry: false,
  });
  const settings = useQuery({
    queryKey: ["agenda-settings"],
    queryFn: getAgendaSettings,
    retry: false,
  });
  const orders = useQuery({
    queryKey: ["orders", "seller", "new"],
    queryFn: () => getOrders("seller", "new"),
    retry: false,
  });
  const wallet = useQuery({ queryKey: ["wallet"], queryFn: getWallet, retry: false });

  if (pro.isPending) return <Skeleton className="rounded-card h-96" />;
  if (pro.isError || !pro.data) {
    return (
      <EmptyState
        icon={<Scissors size={44} />}
        title={t("noSpace")}
        description={t("noSpaceHelp")}
        action={
          <Link href="/pro/start" className={buttonClasses({ size: "lg" })}>
            {t("start")}
          </Link>
        }
      />
    );
  }
  const data = pro.data;
  const published = data.status === "published";
  const zone = agenda.data?.pro.timezone ?? data.opening.time_zone;
  const pending = agenda.data?.pending ?? [];
  const appointments = (agenda.data?.appointments ?? []).filter(
    (a) => !["cancelled", "declined", "expired"].includes(a.status),
  );
  const newOrders = orders.data?.results?.length ?? 0;
  const money = wallet.data?.wallets[0];
  const shortLink = data.short_link ?? "";

  const copy = async () => {
    await navigator.clipboard?.writeText(shortLink);
    toast(t("copied"), "success");
  };
  const share = async () => {
    if (navigator.share) {
      await navigator.share({ title: data.business_name, url: shortLink }).catch(() => undefined);
    } else await copy();
  };
  const confirm = async (id: string) => {
    setBusy(id);
    try {
      await confirmAppointment(id);
      await queryClient.invalidateQueries({ queryKey: ["agenda"] });
      toast(t("confirmed"), "success");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-start gap-2">
            <h1 className="font-display text-headline lg:text-display">{t("title")}</h1>
            <SpeakButton text={`${t("title")}. ${t("pendingCount", { count: pending.length })}`} />
          </div>
          <p className="mt-1">{t("pendingCount", { count: pending.length })}</p>
        </div>
        <Link
          href="/pro/agenda"
          className={buttonClasses({
            variant: pending.length > 0 ? "secondary" : "primary",
            className: "max-sm:w-full",
          })}
        >
          <CalendarPlus aria-hidden size={22} />
          {t("addAppointment")}
        </Link>
      </header>

      {welcome && (
        <section
          aria-labelledby="welcome-title"
          className="bg-poudre rounded-card flex flex-col items-center gap-3 p-5 text-center"
        >
          <Bloom label={t("welcomeTitle")} />
          <h2 id="welcome-title" className="text-title font-bold">
            {t("welcomeTitle")}
          </h2>
          <p>{published ? t("welcomeLive") : t("welcomeNext")}</p>
        </section>
      )}

      {settings.data?.online_paused && (
        <p
          role="status"
          className="bg-poudre rounded-card flex items-center gap-3 p-4 font-semibold"
        >
          <PauseCircle aria-hidden size={28} className="text-alerte shrink-0" />
          <span className="flex-1">{t("paused")}</span>
          <Link href="/pro/creneaux" className="underline">
            {t("pausedChange")}
          </Link>
        </p>
      )}

      {!published && (
        <section
          aria-labelledby="draft-title"
          className="border-alerte rounded-card flex flex-col gap-3 border-2 p-4"
        >
          <h2 id="draft-title" className="flex items-center gap-2 font-bold">
            <WarningCircle aria-hidden size={26} weight="fill" className="text-alerte" />
            {t("draftTitle")}
          </h2>
          <p>{t("draftText", { count: data.missing.length })}</p>
          <Link href="/pro/ma-page" className={buttonClasses({ size: "lg", fullWidth: true })}>
            {t("draftCta")}
          </Link>
        </section>
      )}

      <dl className="border-trait rounded-card grid grid-cols-2 border lg:grid-cols-4">
        {(
          [
            [t("pendingTitle"), String(pending.length)],
            [t("kpiDay"), String(appointments.length)],
            [t("kpiOrders"), String(newOrders)],
            [
              t("kpiMoney"),
              money ? formatMoney(money.available_minor, money.currency, locale) : "–",
            ],
          ] as const
        ).map(([label, value], index) => (
          <div
            key={label}
            className={cn(
              "border-trait flex flex-col gap-0.5 p-4",
              index % 2 === 1 && "border-l",
              index > 1 && "max-lg:border-t",
              index === 2 && "lg:border-l",
            )}
          >
            <dt className="text-small text-prune-doux">{label}</dt>
            <dd className="text-title font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>

      <DayStrip appointments={appointments} zone={zone} locale={locale} label={t("dayStrip")} />

      <nav aria-label={t("shortcuts")} className="flex flex-wrap gap-2">
        {(
          [
            ["/pro/creneaux", "openSlot", <ClockClockwise key="b" size={20} />],
            ["/pro/services", "addService", <Scissors key="c" size={20} />],
            ["/pro/shop/product/new", "addProduct", <Plus key="d" size={20} />],
          ] as const
        ).map(([href, key, icon]) => (
          <Link
            key={key}
            href={href}
            className="press bg-poudre rounded-button text-small flex min-h-11 items-center gap-2 px-3 font-semibold"
          >
            <span aria-hidden className="inline-flex">
              {icon}
            </span>
            {t(key)}
          </Link>
        ))}
      </nav>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-w-0 flex-col gap-5">
          <Card
            id="pending-title"
            title={t("pendingTitle")}
            action={
              pending.length > 0 ? (
                <span className="text-small font-semibold tabular-nums">{pending.length}</span>
              ) : undefined
            }
          >
            {agenda.isPending ? (
              <Skeleton className="h-24" />
            ) : pending.length === 0 ? (
              <p className="text-prune-doux flex items-center gap-2">
                <CheckCircle aria-hidden size={24} />
                {t("pendingEmpty")}
              </p>
            ) : (
              <ul className="flex flex-col gap-3">
                {pending.map((a, index) => (
                  <li
                    key={a.id}
                    className="border-trait flex flex-col gap-2 border-b pb-3 last:border-b-0"
                  >
                    <p className="font-bold">{a.client_name}</p>
                    <p>
                      {a.service_name}
                      <span className="text-prune-doux block">
                        {t("when", {
                          day: dayName(localDay(a.starts_at, zone), locale),
                          time: timeAt(a.starts_at, zone, locale),
                        })}
                      </span>
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        variant={index === 0 ? "primary" : "secondary"}
                        disabled={busy === a.id}
                        onClick={() => void confirm(a.id)}
                      >
                        {t("confirm")}
                      </Button>
                      <Link href={link(a)} className={buttonClasses({ variant: "secondary" })}>
                        {t("otherChoice")}
                      </Link>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card
            id="day-title"
            title={t("dayTitle")}
            action={
              <Link
                href="/pro/agenda"
                className="inline-flex min-h-12 items-center font-semibold underline"
              >
                {t("seeAgenda")}
              </Link>
            }
          >
            {agenda.isPending ? (
              <Skeleton className="h-24" />
            ) : appointments.length === 0 ? (
              <p className="text-prune-doux flex items-center gap-2">
                <CalendarCheck aria-hidden size={24} />
                {t("dayEmpty")}
              </p>
            ) : (
              <ul className="flex flex-col">
                {appointments.map((a) => (
                  <li key={a.id}>
                    <Link
                      href={link(a)}
                      className="hover:bg-poudre border-trait flex min-h-14 items-center gap-3 border-b py-2 last:border-b-0"
                    >
                      <span className="w-16 shrink-0 font-bold">
                        {timeAt(a.starts_at, zone, locale)}
                      </span>
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="truncate font-semibold">{a.client_name}</span>
                        <span className="text-small text-prune-doux truncate">
                          {a.service_name}
                        </span>
                      </span>
                      <span className="text-small shrink-0">
                        {a.arrived_at ? t("arrived") : tStatus(a.status)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="flex min-w-0 flex-col gap-5">
          <Card id="link-title" title={t("linkTitle")}>
            {data.slug && published ? (
              <>
                <div className="flex items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element -- a code drawn by the server */}
                  <img
                    src={printableUrl(data.slug, "card.png")}
                    alt=""
                    loading="lazy"
                    className="rounded-field bg-poudre aspect-square w-24 shrink-0 object-cover"
                  />
                  <p className="min-w-0 font-semibold break-all">
                    {shortLink.replace(/^https?:\/\//, "")}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Button variant="secondary" onClick={() => void copy()}>
                    <Copy aria-hidden size={22} />
                    {t("copy")}
                  </Button>
                  <Button variant="secondary" onClick={() => void share()}>
                    <ShareNetwork aria-hidden size={22} />
                    {t("share")}
                  </Button>
                </div>
                <a
                  href={printableUrl(data.slug, "poster.pdf", true)}
                  className="inline-flex min-h-12 items-center gap-2 font-semibold underline"
                >
                  <QrCode aria-hidden size={24} />
                  {t("poster")}
                </a>
              </>
            ) : (
              <p className="text-prune-doux">{t("linkAfterPublish")}</p>
            )}
          </Card>

          <Card id="shop-title" title={t("shopTitle")}>
            <Link
              href="/pro/shop"
              className="hover:bg-poudre flex min-h-12 items-center gap-3 font-semibold"
            >
              <Package aria-hidden size={26} />
              {t("newOrders", { count: newOrders })}
            </Link>
            <Link
              href="/pro/wallet"
              className="hover:bg-poudre flex min-h-12 items-center gap-3 font-semibold"
            >
              <Wallet aria-hidden size={26} />
              {money
                ? t("available", {
                    amount: formatMoney(money.available_minor, money.currency, locale),
                  })
                : t("wallet")}
            </Link>
          </Card>
        </div>
      </div>
    </div>
  );
}
