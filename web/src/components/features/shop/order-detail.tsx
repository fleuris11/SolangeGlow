"use client";

import {
  Camera,
  CheckCircle,
  Circle,
  CookingPot,
  CreditCard,
  MapPin,
  Package,
  Phone,
  Star,
  Storefront,
  Waveform,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useRef, useState } from "react";

import { BuyerActions, SellerActions } from "@/components/features/payments/payment-actions";
import { DisputePanel } from "@/components/features/payments/payment-detail";
import { ReceiptCode } from "@/components/features/payments/payment-parts";
import { sendPicture } from "@/components/features/payments/upload";
import { Avatar } from "@/components/ui/avatar";
import { Button, buttonClasses } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import type { Payment } from "@/lib/api/payments";
import {
  getOrder,
  orderReady,
  payOrder,
  prepareOrder,
  shipOrder,
  type Order,
} from "@/lib/api/shop";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc, voiceSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

const VideoPlayer = dynamic(() =>
  import("@/components/features/pros/showcase/video-player").then((m) => m.VideoPlayer),
);

/** Paid, being prepared, shipped (or ready to pick up), handed over. */
function OrderSteps({ order }: { order: Order }) {
  const t = useTranslations("shop.steps");
  const pickup = order.delivery_mode === "pickup";
  const reached = ["new", "preparing", "shipped", "ready", "completed", "disputed", "refunded"];
  const done = {
    paid: reached.includes(order.status),
    preparing: !!order.preparing_at || ["shipped", "ready", "completed"].includes(order.status),
    sent: !!order.payment?.shipped_at,
    handed: order.status === "completed",
  };
  const steps = [
    ["paid", t("paid")],
    ["preparing", t("preparing")],
    ["sent", pickup ? t("ready") : t("shipped")],
    ["handed", t("handed")],
  ] as const;
  return (
    <ol className="flex flex-col gap-2" aria-label={t("label")}>
      {steps.map(([key, label]) => (
        <li key={key} className="flex items-center gap-2">
          {done[key] ? (
            <CheckCircle aria-hidden size={24} weight="fill" className="text-feuille" />
          ) : (
            <Circle aria-hidden size={24} className="text-prune-doux" />
          )}
          <span className={cn(done[key] ? "font-bold" : "text-prune-doux")}>{label}</span>
          <span className="sr-only">{done[key] ? t("yes") : t("no")}</span>
        </li>
      ))}
    </ol>
  );
}

function Amounts({ order }: { order: Order }) {
  const t = useTranslations("shop.amounts");
  const locale = useLocale();
  const money = (value: number) => formatMoney(value, order.currency, locale);
  const payment = order.payment;
  const rows: [string, string, boolean?][] = [
    [t("items"), money(order.subtotal_minor)],
    ...(order.discount_minor
      ? [
          [t("discount", { code: order.promo_code }), `− ${money(order.discount_minor)}`] as [
            string,
            string,
          ],
        ]
      : []),
    [t("delivery"), order.delivery_minor ? money(order.delivery_minor) : t("free")],
  ];
  if (order.role === "buyer") {
    rows.push([t("protection"), money(order.buyer_fee_minor)]);
    rows.push([t("total"), money(order.total_minor), true]);
  } else if (payment?.seller_net_minor !== null && payment?.seller_net_minor !== undefined) {
    rows.push([t("commission"), `− ${money(payment.commission_minor ?? 0)}`]);
    rows.push([t("net"), money(payment.seller_net_minor), true]);
  }
  return (
    <dl className="border-trait rounded-card flex flex-col gap-2 border p-4">
      {rows.map(([label, value, strong]) => (
        <div key={label} className={cn("flex justify-between gap-4", strong && "font-bold")}>
          <dt>{label}</dt>
          <dd className="text-right">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function HandOverInfo({ order }: { order: Order }) {
  const t = useTranslations("shop.handover");
  const tModes = useTranslations("shop.modes");
  const pickup = order.pickup;
  const voice = voiceSrc(pickup?.landmarks_voice);
  return (
    <section aria-labelledby="handover" className="flex flex-col gap-3">
      <h2 id="handover" className="text-title font-bold">
        {order.delivery_mode === "partner" && order.partner_name
          ? tModes("partnerNamed", { name: order.partner_name })
          : tModes(order.delivery_mode)}
      </h2>
      {pickup ? (
        <>
          <p className="flex items-start gap-2">
            <Storefront aria-hidden size={22} className="text-hibiscus mt-0.5 shrink-0" />
            {[pickup.address, pickup.district, pickup.city].filter(Boolean).join(", ")}
          </p>
          {pickup.note && <p className="text-prune-doux">{pickup.note}</p>}
          {pickup.landmarks && <p className="bg-poudre rounded-2xl p-3">{pickup.landmarks}</p>}
          {voice && (
            <div className="flex flex-col gap-2">
              <p className="text-small flex items-center gap-1 font-bold">
                <Waveform aria-hidden size={18} className="text-hibiscus" />
                {t("voice")}
              </p>
              <audio controls preload="none" src={voice} className="w-full">
                <track kind="captions" />
              </audio>
            </div>
          )}
          {pickup.itinerary_video?.status === "ready" && (
            <VideoPlayer media={pickup.itinerary_video} label={t("video")} />
          )}
          {pickup.latitude !== null && pickup.longitude !== null && (
            <a
              href={`https://www.google.com/maps/dir/?api=1&destination=${pickup.latitude},${pickup.longitude}`}
              target="_blank"
              rel="noreferrer"
              className={buttonClasses({ variant: "secondary" })}
            >
              <MapPin aria-hidden size={22} weight="bold" />
              {t("directions")}
            </a>
          )}
        </>
      ) : (
        <>
          {order.zone_name && <p className="font-bold">{order.zone_name}</p>}
          {order.address && (
            <p className="flex items-start gap-2">
              <MapPin aria-hidden size={22} className="text-hibiscus mt-0.5 shrink-0" />
              {order.address}
            </p>
          )}
          {order.landmarks && <p className="bg-poudre rounded-2xl p-3">{order.landmarks}</p>}
          {order.role === "seller" && order.contact_phone && (
            <a
              href={`tel:${order.contact_phone}`}
              className={buttonClasses({ variant: "secondary" })}
            >
              <Phone aria-hidden size={22} weight="bold" />
              {t("call", { phone: order.contact_phone })}
            </a>
          )}
        </>
      )}
      {order.note && (
        <p className="border-trait rounded-2xl border p-3">
          <span className="font-bold">{t("note")} </span>
          {order.note}
        </p>
      )}
    </section>
  );
}

/** What the seller does now: prepare, ship with a parcel photo, or « ready to pick up ». */
function SellerSteps({ order, onChange }: { order: Order; onChange: (o: Order) => void }) {
  const t = useTranslations("shop.seller");
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [carrier, setCarrier] = useState(order.partner_name);
  const [tracking, setTracking] = useState("");
  const [proof, setProof] = useState<string | null>(null);
  const proofInput = useRef<HTMLInputElement>(null);
  const can = order.can;

  const run = async (step: () => Promise<Order>, done: string) => {
    setBusy(true);
    try {
      onChange(await step());
      toast(done, "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {can.prepare && (
        <Button
          size="lg"
          fullWidth
          disabled={busy}
          onClick={() => void run(() => prepareOrder(order.id), t("preparingDone"))}
        >
          <CookingPot aria-hidden size={24} weight="bold" />
          {t("prepare")}
        </Button>
      )}
      {can.ready && (
        <Button
          size="lg"
          fullWidth
          variant={can.prepare ? "secondary" : "primary"}
          disabled={busy}
          onClick={() => void run(() => orderReady(order.id), t("readyDone"))}
        >
          <Storefront aria-hidden size={24} weight="bold" />
          {t("ready")}
        </Button>
      )}
      {can.ship && (
        <form
          className="border-trait rounded-card flex flex-col gap-3 border p-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!proof) return;
            void run(
              () => shipOrder(order.id, { proof, carrier, tracking_number: tracking }),
              t("shippedDone"),
            );
          }}
        >
          <h2 className="text-title flex items-center gap-2 font-bold">
            <Package aria-hidden size={24} weight="bold" />
            {t("shipTitle")}
          </h2>
          <input
            ref={proofInput}
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            tabIndex={-1}
            aria-label={t("photo")}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (!file) return;
              setBusy(true);
              sendPicture(file, "delivery_proof")
                .then((id) => {
                  setProof(id);
                  toast(t("photoAdded"), "success");
                })
                .catch(() => toast(t("photoError"), "warning"))
                .finally(() => setBusy(false));
            }}
          />
          <Button
            variant={proof ? "quiet" : "secondary"}
            disabled={busy}
            onClick={() => proofInput.current?.click()}
          >
            <Camera aria-hidden size={22} weight="bold" />
            {proof ? t("photoAgain") : t("photo")}
          </Button>
          {proof && (
            <p className="text-feuille flex items-center gap-2 font-bold">
              <CheckCircle aria-hidden size={22} weight="fill" />
              {t("photoOk")}
            </p>
          )}
          <Input
            label={t("carrier")}
            value={carrier}
            maxLength={80}
            onChange={(e) => setCarrier(e.target.value)}
          />
          <Input
            label={t("tracking")}
            value={tracking}
            maxLength={80}
            onChange={(e) => setTracking(e.target.value)}
          />
          <Button type="submit" size="lg" disabled={busy || !proof}>
            {t("ship")}
          </Button>
        </form>
      )}
    </div>
  );
}

/** One order, seen by the client or by the seller, with its secure payment. */
export function OrderDetail({ orderId }: { orderId: string }) {
  const t = useTranslations("shop.detail");
  const tStatus = useTranslations("shop.status");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = ["order", orderId];
  const query = useQuery({
    queryKey: key,
    queryFn: () => getOrder(orderId),
    refetchInterval: (q) => (q.state.data?.status === "pending_payment" ? 4000 : false),
  });
  const setOrder = (order: Order) => queryClient.setQueryData(key, order);
  const setPayment = (payment: Payment) => {
    // The money moved: the order follows (its status comes back with it).
    const current = queryClient.getQueryData<Order>(key);
    if (current) setOrder({ ...current, payment });
    void queryClient.invalidateQueries({ queryKey: key });
  };

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
  const buyer = order.role === "buyer";
  const other = buyer ? order.shop.name : order.buyer.name;
  const otherPhoto = buyer ? order.shop.photo : order.buyer.photo;

  const payAgain = async () => {
    try {
      const result = await payOrder(order.id);
      window.location.assign(result.checkout_url);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-mention text-prune-doux font-bold">
          {t("reference", {
            reference: order.reference,
            date: new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
              new Date(order.created_at),
            ),
          })}
        </p>
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex-1 font-bold">{tStatus(order.status)}</h1>
          <SpeakButton
            text={`${tStatus(order.status)}. ${t(buyer ? "from" : "for", { name: other })}`}
          />
        </div>
        <p className="flex items-center gap-2">
          <Avatar name={other} src={mediaSrc(otherPhoto, "thumb")} size="sm" />
          {t(buyer ? "from" : "for", { name: other })}
        </p>
      </header>

      {order.can.pay && (
        <div className="flex flex-col gap-2">
          <p className="bg-poudre rounded-2xl p-3">{t("notPaid")}</p>
          <Button size="lg" fullWidth onClick={() => void payAgain()}>
            <CreditCard aria-hidden size={24} weight="bold" />
            {t("pay", { amount: formatMoney(order.total_minor, order.currency, locale) })}
          </Button>
        </div>
      )}

      {payment?.receipt_code && <ReceiptCode code={payment.receipt_code} />}
      {!["pending_payment", "cancelled"].includes(order.status) && <OrderSteps order={order} />}

      {!buyer && <SellerSteps order={order} onChange={setOrder} />}

      <section aria-labelledby="lines" className="flex flex-col gap-3">
        <h2 id="lines" className="text-title font-bold">
          {t("lines", { count: order.lines.length })}
        </h2>
        <ul className="flex flex-col gap-3">
          {order.lines.map((line) => (
            <li key={line.id} className="flex gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
              <img
                src={mediaSrc(line.photo, "thumb")}
                alt=""
                className="bg-poudre size-16 shrink-0 rounded-xl object-cover"
              />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-bold">{line.title}</span>
                {line.variant_label && (
                  <span className="text-small text-prune-doux">{line.variant_label}</span>
                )}
                <span className="text-small">
                  {t("quantity", {
                    count: line.quantity,
                    price: formatMoney(line.unit_price_minor, order.currency, locale),
                  })}
                </span>
              </span>
              <span className="font-bold">
                {formatMoney(line.total_minor, order.currency, locale)}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <Amounts order={order} />
      <HandOverInfo order={order} />

      {order.shipping_proof && (
        <section aria-labelledby="proof" className="flex flex-col gap-2">
          <h2 id="proof" className="font-bold">
            {t("proof")}
          </h2>
          {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
          <img
            src={mediaSrc(order.shipping_proof, "medium")}
            alt={t("proof")}
            className="max-h-72 rounded-2xl"
          />
        </section>
      )}
      {payment?.carrier && (
        <p>
          {payment.tracking_number
            ? t("carrier", { carrier: payment.carrier, tracking: payment.tracking_number })
            : t("carrierOnly", { carrier: payment.carrier })}
        </p>
      )}

      {payment && <DisputePanel payment={payment} onChange={setPayment} />}
      {payment &&
        (buyer ? (
          <BuyerActions payment={payment} onChange={setPayment} />
        ) : (
          <SellerActions payment={payment} onChange={setPayment} />
        ))}

      {buyer && order.status === "completed" && (
        <Link href="/me/reviews" className={buttonClasses({ variant: "secondary" })}>
          <Star aria-hidden size={22} weight="bold" />
          {t("review")}
        </Link>
      )}
      {payment && (
        <Link href={`/payments/${payment.id}`} className="text-prune-doux self-start underline">
          {t("payment")}
        </Link>
      )}
    </div>
  );
}
