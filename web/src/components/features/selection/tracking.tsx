"use client";

import { CheckCircle, Circle, MapPin, Package } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { BuyerActions } from "@/components/features/payments/payment-actions";
import { DisputePanel } from "@/components/features/payments/payment-detail";
import { ReceiptCode } from "@/components/features/payments/payment-parts";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import type { Payment } from "@/lib/api/payments";
import {
  cancelSelectionOrder,
  getSelectionOrder,
  getSelectionOrders,
  paySelectionOrder,
  type SelectionOrder,
} from "@/lib/api/selection";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

import { shortDate } from "./dates";

/** Every Selection order of the client, newest first. */
export function SelectionOrders() {
  const t = useTranslations("selection.orders");
  const tStatus = useTranslations("selection.status");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["selection-orders"], queryFn: getSelectionOrders });
  if (query.isPending) return <Skeleton className="rounded-card h-60" />;
  const rows = query.data?.results ?? [];
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      {rows.length === 0 ? (
        <EmptyState
          icon={<Package size={44} weight="duotone" />}
          title={t("empty")}
          action={
            <Link href="/selection" className={buttonClasses({ size: "lg" })}>
              {t("discover")}
            </Link>
          }
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((order) => (
            <li key={order.id}>
              <Link
                href={`/selection/orders/${order.id}`}
                className="border-trait hover:bg-poudre rounded-card flex min-h-16 items-center gap-3 border p-3"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
                <img
                  src={mediaSrc(order.photo, "thumb")}
                  alt=""
                  className="bg-poudre size-14 shrink-0 rounded-xl object-cover"
                />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate font-bold">{order.title}</span>
                  <span className="text-small font-bold">{tStatus(order.status)}</span>
                </span>
                <span className="shrink-0 font-bold">
                  {formatMoney(order.total_xof, "XOF", locale)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const STEPS = ["paid", "ordered", "received", "shipped", "arrived", "completed"] as const;
const REACHED: Record<string, number> = {
  waiting_group: 0,
  to_order: 0,
  ordered: 1,
  received: 2,
  shipped: 3,
  arrived: 4,
  completed: 5,
  disputed: 3,
};

function Steps({ order }: { order: SelectionOrder }) {
  const t = useTranslations("selection.steps");
  const reached = REACHED[order.status] ?? -1;
  return (
    <ol className="flex flex-col gap-2" aria-label={t("label")}>
      {STEPS.map((step, index) => {
        const done = index <= reached;
        return (
          <li key={step} className="flex items-center gap-2">
            {done ? (
              <CheckCircle aria-hidden size={24} weight="fill" className="text-feuille" />
            ) : (
              <Circle aria-hidden size={24} className="text-prune-doux" />
            )}
            <span className={cn(done ? "font-bold" : "text-prune-doux")}>{t(step)}</span>
            <span className="sr-only">{done ? t("yes") : t("no")}</span>
          </li>
        );
      })}
    </ol>
  );
}

/** One order: where the parcel is, the receipt code, the pick-up point. */
export function SelectionTracking({ orderId }: { orderId: string }) {
  const t = useTranslations("selection.tracking");
  const tStatus = useTranslations("selection.status");
  const tModes = useTranslations("selection.modes");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = ["selection-order", orderId];
  const query = useQuery({
    queryKey: key,
    queryFn: () => getSelectionOrder(orderId),
    refetchInterval: (q) => (q.state.data?.status === "pending_payment" ? 3000 : false),
  });
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (query.isError || !query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const order = query.data;
  const payment = order.payment;
  const money = (value: number) => formatMoney(value, "XOF", locale);
  const setPayment = (next: Payment) => {
    queryClient.setQueryData(key, { ...order, payment: next });
    void queryClient.invalidateQueries({ queryKey: key });
  };
  const run = async (step: () => Promise<SelectionOrder>, done?: string) => {
    setBusy(true);
    try {
      const next = await step();
      queryClient.setQueryData(key, next);
      if (done) toast(done, "success");
      return next;
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      return null;
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-mention text-prune-doux font-bold">{order.reference}</p>
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex-1 font-bold">{tStatus(order.status)}</h1>
          <SpeakButton text={`${order.title}. ${tStatus(order.status)}`} />
        </div>
        <p className="font-bold">
          {order.title}
          {order.option && ` (${order.option})`} x{order.quantity}
        </p>
        <p>{money(order.total_xof)}</p>
      </header>

      {order.can.pay && (
        <Button
          size="lg"
          fullWidth
          disabled={busy}
          onClick={() =>
            void run(() => paySelectionOrder(order.id)).then((next) => {
              const url = next?.payment?.checkout_url;
              if (url) window.location.assign(url);
            })
          }
        >
          {t("pay", { amount: money(order.total_xof) })}
        </Button>
      )}

      {order.group && order.status === "waiting_group" && (
        <p className="bg-poudre rounded-2xl p-3">
          {t("group", {
            count: order.group.count,
            target: order.group.target,
            date: shortDate(order.group.ends_at, locale),
          })}
        </p>
      )}

      {payment?.receipt_code && <ReceiptCode code={payment.receipt_code} />}
      {!["pending_payment", "cancelled", "refunded"].includes(order.status) && (
        <Steps order={order} />
      )}

      {order.estimate_from && order.estimate_to && order.status !== "completed" && (
        <p>
          {t("expected", {
            mode: tModes(order.shipping_mode),
            from: shortDate(order.estimate_from, locale),
            to: shortDate(order.estimate_to, locale),
          })}
        </p>
      )}
      {order.tracking_number && (
        <p className="border-trait rounded-2xl border p-3">
          {t("trackingLine", { carrier: order.carrier, tracking: order.tracking_number })}
        </p>
      )}

      <section aria-labelledby="pickup" className="flex flex-col gap-2">
        <h2 id="pickup" className="text-title flex items-center gap-2 font-bold">
          <MapPin aria-hidden size={24} weight="duotone" className="text-hibiscus" />
          {t("pickup")}
        </h2>
        <p className="font-bold">{order.pickup_point.name}</p>
        <p>{[order.pickup_point.address, order.pickup_point.city].join(", ")}</p>
        {order.pickup_point.landmarks && (
          <p className="text-prune-doux">{order.pickup_point.landmarks}</p>
        )}
        {order.pickup_point.hours && <p className="text-prune-doux">{order.pickup_point.hours}</p>}
      </section>

      {order.can.cancel && (
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() => void run(() => cancelSelectionOrder(order.id), t("cancelled"))}
        >
          {t("cancel")}
        </Button>
      )}
      {payment && <DisputePanel payment={payment} onChange={setPayment} />}
      {payment && !order.can.cancel && <BuyerActions payment={payment} onChange={setPayment} />}
    </div>
  );
}
