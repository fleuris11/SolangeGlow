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
        <h2 id={id} className="text-title font-bold">
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
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
        icon={<Scissors size={44} weight="duotone" />}
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
    <div className="flex flex-col gap-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-display">{t("title")}</h1>
          <p className="text-prune-doux">{data.business_name}</p>
        </div>
        <SpeakButton text={`${t("title")}. ${t("pendingCount", { count: pending.length })}`} />
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
          <PauseCircle aria-hidden size={28} weight="duotone" className="text-alerte shrink-0" />
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

      <nav aria-label={t("shortcuts")} className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {(
          [
            ["/pro/agenda", "addAppointment", <CalendarPlus key="a" size={26} weight="duotone" />],
            ["/pro/creneaux", "openSlot", <ClockClockwise key="b" size={26} weight="duotone" />],
            ["/pro/services", "addService", <Scissors key="c" size={26} weight="duotone" />],
            ["/pro/shop/product/new", "addProduct", <Plus key="d" size={26} weight="bold" />],
          ] as const
        ).map(([href, key, icon]) => (
          <Link
            key={key}
            href={href}
            className="press border-trait hover:bg-poudre rounded-card flex min-h-20 flex-col justify-center gap-1 border p-3 font-semibold"
          >
            <span aria-hidden className="text-hibiscus inline-flex">
              {icon}
            </span>
            {t(key)}
          </Link>
        ))}
      </nav>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="flex min-w-0 flex-col gap-6">
          <Card
            id="pending-title"
            title={t("pendingTitle")}
            action={
              pending.length > 0 ? (
                <span className="bg-rouge text-sur-hibiscus rounded-full px-3 py-1 font-bold">
                  {pending.length}
                </span>
              ) : undefined
            }
          >
            {agenda.isPending ? (
              <Skeleton className="h-24" />
            ) : pending.length === 0 ? (
              <p className="text-prune-doux flex items-center gap-2">
                <CheckCircle aria-hidden size={24} weight="duotone" className="text-feuille" />
                {t("pendingEmpty")}
              </p>
            ) : (
              <ul className="flex flex-col gap-3">
                {pending.map((a) => (
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
                      <Button disabled={busy === a.id} onClick={() => void confirm(a.id)}>
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
                <CalendarCheck aria-hidden size={24} weight="duotone" />
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

        <div className="flex min-w-0 flex-col gap-6">
          <Card id="link-title" title={t("linkTitle")}>
            {data.slug && published ? (
              <>
                <p className="font-semibold break-all">{shortLink.replace(/^https?:\/\//, "")}</p>
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
                  <QrCode aria-hidden size={24} weight="duotone" />
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
              <Package aria-hidden size={26} weight="duotone" className="text-hibiscus" />
              {t("newOrders", { count: newOrders })}
            </Link>
            <Link
              href="/pro/wallet"
              className="hover:bg-poudre flex min-h-12 items-center gap-3 font-semibold"
            >
              <Wallet aria-hidden size={26} weight="duotone" className="text-hibiscus" />
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
