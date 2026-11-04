"use client";

import { CheckCircle, QrCode, UserCircle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getArrival, markArrival } from "@/lib/api/booking";
import { dayName, localDay, timeAt } from "@/lib/booking/time";

/** What the pro sees after scanning the QR code a client shows: check, then mark her arrival. */
export function ArrivalScreen({ reference }: { reference: string }) {
  const t = useTranslations("booking.arrival");
  const tStatus = useTranslations("booking.status");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = ["arrival", reference];
  const query = useQuery({ queryKey: key, queryFn: () => getArrival(reference), retry: false });
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (query.isError || !query.data) {
    return (
      <EmptyState
        icon={<QrCode size={44} />}
        title={t("notFound")}
        description={t("notFoundHelp")}
      />
    );
  }
  const a = query.data.appointment;
  const zone = a.pro.timezone;
  const when = t("when", {
    day: dayName(localDay(a.starts_at, zone), locale),
    time: timeAt(a.starts_at, zone, locale),
  });
  const arrived = a.arrived_at !== null;

  const mark = async () => {
    setBusy(true);
    try {
      await markArrival(reference);
      await queryClient.invalidateQueries({ queryKey: key });
      toast(t("done"), "success");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="flex flex-col gap-6">
      <header className="flex items-center gap-3">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${a.client_name}, ${a.service_name}, ${when}`} />
      </header>
      <dl className="border-trait rounded-card flex flex-col gap-3 border p-4">
        <div>
          <dt className="sr-only">{t("client")}</dt>
          <dd className="text-lead flex items-center gap-2 font-bold">
            <UserCircle aria-hidden size={28} />
            {a.client_name}
          </dd>
        </div>
        <div>
          <dt className="text-small text-prune-doux">{t("service")}</dt>
          <dd className="font-bold">{a.service_name}</dd>
        </div>
        <div>
          <dt className="text-small text-prune-doux">{t("time")}</dt>
          <dd className="font-bold">{when}</dd>
        </div>
        <div>
          <dt className="text-small text-prune-doux">{t("status")}</dt>
          <dd className="font-bold">{tStatus(a.status)}</dd>
        </div>
      </dl>
      {arrived ? (
        <p role="status" className="text-feuille flex items-center gap-2 font-bold">
          <CheckCircle aria-hidden size={28} weight="fill" />
          {t("arrivedAt", { time: timeAt(a.arrived_at!, zone, locale) })}
        </p>
      ) : a.status === "confirmed" ? (
        <Button size="lg" fullWidth disabled={busy} onClick={() => void mark()}>
          <CheckCircle aria-hidden size={26} weight="bold" />
          {t("mark")}
        </Button>
      ) : (
        <p className="text-prune-doux">{t("notConfirmed")}</p>
      )}
    </article>
  );
}
