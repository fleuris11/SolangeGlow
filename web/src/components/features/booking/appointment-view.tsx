"use client";

import {
  CalendarCheck,
  CalendarX,
  CheckCircle,
  Clock,
  CreditCard,
  HourglassMedium,
  MapPin,
  ShoppingBag,
  Star,
  WarningCircle,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { MySalonItems } from "@/components/features/glowpro/my-salon-items";
import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  acceptOffer,
  answerProposal,
  cancelAppointment,
  getGuestAppointment,
  getMyAppointment,
  getMyAppointments,
  getMyWaitlist,
  leaveWaitlist,
  payDeposit,
  type Appointment,
  type AppointmentStatus,
  type Holder,
} from "@/lib/api/booking";
import { dayName, localDay, timeAt } from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

const STATUS_ICON: Record<AppointmentStatus, ReactNode> = {
  pending: <HourglassMedium aria-hidden size={28} weight="duotone" className="text-alerte" />,
  awaiting_deposit: <CreditCard aria-hidden size={28} weight="duotone" className="text-alerte" />,
  confirmed: <CheckCircle aria-hidden size={28} weight="fill" className="text-feuille" />,
  proposed: <Clock aria-hidden size={28} weight="duotone" className="text-hibiscus" />,
  held: <Clock aria-hidden size={28} weight="duotone" className="text-hibiscus" />,
  declined: <CalendarX aria-hidden size={28} weight="duotone" className="text-alerte" />,
  cancelled: <CalendarX aria-hidden size={28} weight="duotone" className="text-alerte" />,
  completed: <CheckCircle aria-hidden size={28} weight="fill" className="text-feuille" />,
  no_show: <WarningCircle aria-hidden size={28} weight="duotone" className="text-alerte" />,
  expired: <CalendarX aria-hidden size={28} weight="duotone" className="text-prune-doux" />,
};

function paymentKey(status: string): "held" | "refunded" | "released" | "pending" {
  return status === "held" || status === "refunded" || status === "released" ? status : "pending";
}

/** « samedi 11 janvier », « 10 h 30 »: the parts of the « when » message, at the salon. */
export function whenParts(moment: string, zone: string, locale: string) {
  return { day: dayName(localDay(moment, zone), locale), time: timeAt(moment, zone, locale) };
}

/** One appointment, seen by the client (signed in) or the guest (her link). */
export function AppointmentView({ holder }: { holder: Holder }) {
  const t = useTranslations("booking.appointment");
  const tFlow = useTranslations("booking.flow");
  const tStatus = useTranslations("booking.status");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = ["appointment", "id" in holder ? holder.id : holder.token];
  const query = useQuery({
    queryKey: key,
    queryFn: () =>
      "id" in holder ? getMyAppointment(holder.id) : getGuestAppointment(holder.token),
    retry: false,
  });
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [bloom, setBloom] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (query.isError || !query.data) {
    return (
      <EmptyState
        icon={<CalendarX size={44} weight="duotone" />}
        title={t("notFound")}
        description={t("notFoundHelp")}
      />
    );
  }
  const a = query.data;
  const when = tFlow("when", whenParts(a.starts_at, a.pro.timezone, locale));
  const place = [a.pro.address, a.pro.district, a.pro.city].filter(Boolean).join(", ");
  const title = tStatus(a.status);

  const run = async (action: () => Promise<unknown>, success?: string, petals = false) => {
    setBusy(true);
    try {
      const answer = await action();
      if (answer && typeof answer === "object" && "checkout_url" in answer) {
        const url = (answer as { checkout_url?: string | null }).checkout_url;
        if (url) {
          window.location.assign(url);
          return;
        }
      }
      await queryClient.invalidateQueries({ queryKey: key });
      if (success) toast(success, "success");
      if (petals) setBloom(true);
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
      setAsking(false);
    }
  };

  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        {bloom && <Bloom label={tStatus("confirmed")} className="self-center" />}
        <div className="flex items-center gap-3">
          {STATUS_ICON[a.status]}
          <h1 className="text-headline flex-1 font-bold">{title}</h1>
          <SpeakButton text={`${title}. ${a.service_name}, ${when}`} />
        </div>
        <p className="text-lead font-bold">{a.service_name}</p>
        <p className="flex items-center gap-2">
          <CalendarCheck aria-hidden size={24} weight="duotone" className="text-hibiscus" />
          {when}
        </p>
        <Link href={`/${a.pro.slug}`} className="flex items-center gap-2 font-bold underline">
          {a.pro.name}
        </Link>
        {place && (
          <p className="text-prune-doux flex items-center gap-2">
            <MapPin aria-hidden size={22} />
            {place}
          </p>
        )}
      </header>

      {a.status === "proposed" && (
        <section
          className="bg-poudre rounded-card flex flex-col gap-3 p-4"
          aria-labelledby="proposed"
        >
          <h2 id="proposed" className="font-bold">
            {t("proposed", { name: a.pro.name })}
          </h2>
          {a.pro_message && <p>« {a.pro_message} »</p>}
          {a.proposed_from && (
            <p className="text-small text-prune-doux">
              {t("insteadOf", {
                when: tFlow("when", whenParts(a.proposed_from, a.pro.timezone, locale)),
              })}
            </p>
          )}
          <Button
            size="lg"
            fullWidth
            disabled={busy}
            onClick={() => void run(() => answerProposal(holder, true), t("accepted"), true)}
          >
            {t("accept")}
          </Button>
          <Button
            variant="secondary"
            fullWidth
            disabled={busy}
            onClick={() => void run(() => answerProposal(holder, false), t("refused"))}
          >
            {t("refuse")}
          </Button>
        </section>
      )}

      {a.status === "held" && (
        <section className="bg-poudre rounded-card flex flex-col gap-3 p-4" aria-labelledby="held">
          <h2 id="held" className="font-bold">
            {t("held")}
          </h2>
          <p className="text-small text-prune-doux">{t("heldHelp")}</p>
          <Button
            size="lg"
            fullWidth
            disabled={busy}
            onClick={() => void run(() => acceptOffer(holder), t("booked"), true)}
          >
            {t("take")}
          </Button>
        </section>
      )}

      {a.status === "awaiting_deposit" && "id" in holder && (
        <section
          className="bg-poudre rounded-card flex flex-col gap-3 p-4"
          aria-labelledby="deposit"
        >
          <h2 id="deposit" className="font-bold">
            {t("depositDue", { amount: formatMoney(a.deposit_minor, a.currency, locale) })}
          </h2>
          <p className="text-small text-prune-doux">{t("depositHelp")}</p>
          <Button
            size="lg"
            fullWidth
            disabled={busy}
            onClick={() => void run(() => payDeposit(holder.id))}
          >
            <CreditCard aria-hidden size={26} weight="bold" />
            {t("pay", { amount: formatMoney(a.deposit_minor, a.currency, locale) })}
          </Button>
        </section>
      )}

      {(a.status === "declined" || a.status === "cancelled") && a.pro_message && (
        <p className="bg-poudre rounded-2xl p-3">« {a.pro_message} »</p>
      )}

      <dl className="border-trait rounded-card flex flex-col gap-3 border p-4">
        {a.option_names.length > 0 && (
          <div>
            <dt className="text-small text-prune-doux">{t("options")}</dt>
            <dd className="font-bold">{a.option_names.join(", ")}</dd>
          </div>
        )}
        {a.steps.some((s) => s.staff_name) && (
          <div>
            <dt className="text-small text-prune-doux">{t("with")}</dt>
            <dd className="font-bold">
              {[...new Set(a.steps.map((s) => s.staff_name).filter(Boolean))].join(", ")}
            </dd>
          </div>
        )}
        <div>
          <dt className="text-small text-prune-doux">{t("price")}</dt>
          <dd className="font-bold">
            {a.price_minor === null
              ? tFlow("quote")
              : formatMoney(a.price_minor, a.currency, locale)}
            {a.discount_percent > 0 && ` (-${a.discount_percent} %)`}
          </dd>
        </div>
        {a.deposit_minor > 0 && (
          <div>
            <dt className="text-small text-prune-doux">{t("deposit")}</dt>
            <dd className="font-bold">
              {formatMoney(a.deposit_minor, a.currency, locale)}
              {a.payment && ` (${t(`payment.${paymentKey(a.payment.status)}`)})`}
            </dd>
          </div>
        )}
        <div>
          <dt className="text-small text-prune-doux">{t("reference")}</dt>
          <dd className="font-bold">{a.reference}</dd>
        </div>
      </dl>

      {a.advice.length > 0 && (
        <section aria-labelledby="advice" className="flex flex-col gap-2">
          <h2 id="advice" className="text-lead flex items-center gap-2 font-bold">
            <ShoppingBag aria-hidden size={24} weight="duotone" className="text-hibiscus" />
            {t("advice", { name: a.pro.name })}
          </h2>
          <ul className="flex flex-col gap-2">
            {a.advice.map((item) => (
              <li key={item.product_id}>
                <Link
                  href={`/${a.pro.slug}/shop/${item.slug}`}
                  className="border-trait hover:bg-poudre rounded-card flex min-h-16 flex-col justify-center border p-3"
                >
                  <span className="font-bold">{item.title}</span>
                  {item.note && <span className="text-small text-prune-doux">{item.note}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {a.photos.length > 0 && (
        <ul className="grid grid-cols-3 gap-2" aria-label={t("photos")}>
          {a.photos.map((photo, i) => (
            <li key={i}>
              {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
              <img
                src={mediaSrc(photo, "medium")}
                alt=""
                className="aspect-square w-full rounded-2xl object-cover"
              />
            </li>
          ))}
        </ul>
      )}

      {a.can_review && (
        <Link href="/me/reviews" className={buttonClasses({ size: "lg", fullWidth: true })}>
          <Star aria-hidden size={26} weight="bold" />
          {t("review")}
        </Link>
      )}

      {a.can_cancel && (
        <div className="flex flex-col gap-2">
          <p className="text-small text-prune-doux">
            {a.late_cancel
              ? a.deposit_minor > 0
                ? t("lateRule")
                : t("lateNoDeposit")
              : t("freeUntil", {
                  when: tFlow("when", whenParts(a.free_cancel_until, a.pro.timezone, locale)),
                })}
          </p>
          <Button variant="secondary" fullWidth disabled={busy} onClick={() => setAsking(true)}>
            <CalendarX aria-hidden size={24} />
            {t("cancel")}
          </Button>
        </div>
      )}
      <Sheet
        open={asking}
        onOpenChange={setAsking}
        title={t("cancelTitle")}
        description={
          a.late_cancel && a.deposit_minor > 0
            ? t("cancelLate")
            : a.deposit_minor > 0
              ? t("cancelFree")
              : t("cancelNoDeposit")
        }
      >
        <div className="flex flex-col gap-3">
          <Button
            size="lg"
            fullWidth
            disabled={busy}
            onClick={() => void run(() => cancelAppointment(holder), t("cancelled"))}
          >
            {t("cancelConfirm")}
          </Button>
          <Button variant="quiet" fullWidth onClick={() => setAsking(false)}>
            {t("keep")}
          </Button>
        </div>
      </Sheet>
    </article>
  );
}

/** Her appointments: to come first, then the past ones; her waiting lists. */
export function AppointmentsScreen() {
  const t = useTranslations("booking.list");
  const query = useQuery({ queryKey: ["appointments"], queryFn: getMyAppointments });
  const waiting = useQuery({ queryKey: ["waitlist"], queryFn: getMyWaitlist });
  const queryClient = useQueryClient();
  const locale = useLocale();
  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  const upcoming = query.data?.upcoming ?? [];
  const past = query.data?.past ?? [];
  const lists = waiting.data ?? [];
  return (
    <div className="flex flex-col gap-6">
      <MyAppointments upcoming={upcoming} past={past} />
      <MySalonItems />
      {lists.length > 0 && (
        <section aria-labelledby="waiting" className="flex flex-col gap-2">
          <h2 id="waiting" className="text-title font-bold">
            {t("waiting")}
          </h2>
          <ul className="flex flex-col gap-2">
            {lists.map((entry) => (
              <li
                key={entry.id}
                className="border-trait rounded-card flex min-h-16 items-center gap-3 border p-3"
              >
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="font-bold">{entry.service_name}</span>
                  <span className="text-small">{entry.pro.name}</span>
                  <span className="text-small text-prune-doux">{dayName(entry.day, locale)}</span>
                </span>
                {entry.offer_id ? (
                  <Link href={`/appointments/${entry.offer_id}`} className={buttonClasses({})}>
                    {t("offer")}
                  </Link>
                ) : (
                  <Button
                    variant="quiet"
                    onClick={() =>
                      void leaveWaitlist(entry.id).then(() =>
                        queryClient.invalidateQueries({ queryKey: ["waitlist"] }),
                      )
                    }
                  >
                    {t("leave")}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function MyAppointments({ upcoming, past }: { upcoming: Appointment[]; past: Appointment[] }) {
  const t = useTranslations("booking.list");
  const tFlow = useTranslations("booking.flow");
  const tStatus = useTranslations("booking.status");
  const locale = useLocale();
  const row = (a: Appointment) => (
    <li key={a.id}>
      <Link
        href={`/appointments/${a.id}`}
        className="border-trait hover:bg-poudre rounded-card flex min-h-16 items-center gap-3 border p-3"
      >
        <span className="shrink-0">{STATUS_ICON[a.status]}</span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate font-bold">{a.service_name}</span>
          <span className="text-small truncate">{a.pro.name}</span>
          <span className="text-small text-prune-doux">
            {tFlow("when", whenParts(a.starts_at, a.pro.timezone, locale))}
          </span>
        </span>
        <span
          className={cn(
            "text-small shrink-0 font-bold",
            a.status === "confirmed" && "text-feuille",
          )}
        >
          {tStatus(a.status)}
        </span>
      </Link>
    </li>
  );
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={t("title")} />
      </div>
      {upcoming.length === 0 && past.length === 0 ? (
        <EmptyState
          icon={<CalendarCheck size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
          action={
            <Link href="/explore" className={buttonClasses({ size: "lg" })}>
              {t("explore")}
            </Link>
          }
        />
      ) : (
        <>
          <section aria-labelledby="upcoming" className="flex flex-col gap-2">
            <h2 id="upcoming" className="text-title font-bold">
              {t("upcoming")}
            </h2>
            {upcoming.length ? (
              <ul className="flex flex-col gap-2">{upcoming.map(row)}</ul>
            ) : (
              <p className="text-prune-doux">{t("noUpcoming")}</p>
            )}
          </section>
          {past.length > 0 && (
            <section aria-labelledby="past" className="flex flex-col gap-2">
              <h2 id="past" className="text-title font-bold">
                {t("past")}
              </h2>
              <ul className="flex flex-col gap-2">{past.map(row)}</ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
