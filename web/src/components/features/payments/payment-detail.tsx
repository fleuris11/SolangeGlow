"use client";

import { ChatsCircle, Gavel, Hourglass } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { addEvidence, getPayment, type Payment } from "@/lib/api/payments";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

import { BuyerActions, SellerActions } from "./payment-actions";
import { Breakdown, ReceiptCode, Steps } from "./payment-parts";

export function DisputePanel({
  payment,
  onChange,
}: {
  payment: Payment;
  onChange: (p: Payment) => void;
}) {
  const t = useTranslations("payments.dispute");
  const tReasons = useTranslations("payments.reasons");
  const tDecisions = useTranslations("payments.decisions");
  const locale = useLocale();
  const toast = useToast();
  const [text, setText] = useState("");
  const dispute = payment.dispute;
  if (!dispute) return null;
  const open = dispute.status === "open";

  const send = async () => {
    try {
      onChange(await addEvidence(payment.id, { text }));
      setText("");
      toast(t("added"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  return (
    <section
      aria-labelledby="dispute-title"
      className="border-alerte rounded-card flex flex-col gap-3 border-2 p-4"
    >
      <h2 id="dispute-title" className="text-title flex items-center gap-2 font-bold">
        <Gavel aria-hidden size={24} weight="bold" />
        {open ? t("open") : t("decided")}
      </h2>
      <p>{tReasons(dispute.reason)}</p>
      {open ? (
        <p className="text-small flex items-center gap-2">
          <Hourglass aria-hidden size={18} />
          {t("due", {
            date: new Intl.DateTimeFormat(locale, {
              dateStyle: "medium",
              timeStyle: "short",
            }).format(new Date(dispute.response_due_at)),
          })}
        </p>
      ) : (
        <>
          <p className="font-bold">{tDecisions(dispute.decision ?? "release")}</p>
          {dispute.refund_minor > 0 && (
            <p>
              {t("refunded", {
                amount: formatMoney(dispute.refund_minor, payment.currency, locale),
              })}
            </p>
          )}
        </>
      )}
      {dispute.note && <p className="bg-poudre rounded-2xl p-3">{dispute.note}</p>}
      {dispute.conversation_id && (
        <Link
          href={`/messages/${dispute.conversation_id}`}
          className={buttonClasses({ variant: "secondary" })}
        >
          <ChatsCircle aria-hidden size={22} weight="bold" />
          {t("room")}
        </Link>
      )}
      <h3 className="font-bold">{t("evidence", { count: dispute.evidence.length })}</h3>
      <ul className="flex flex-col gap-2">
        {dispute.evidence.map((item) => (
          <li key={item.id} className="bg-carte border-trait rounded-2xl border p-3">
            <p className="text-mention text-prune-doux">
              {item.author_id === payment.buyer.id
                ? payment.buyer.name
                : item.author_id === payment.seller.id
                  ? payment.seller.name
                  : t("team")}
            </p>
            {item.text && <p className="whitespace-pre-line">{item.text}</p>}
            {item.media && (
              // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
              <img
                src={mediaSrc(item.media, "medium", "thumb")}
                alt={t("photo")}
                className="mt-2 max-h-60 rounded-xl"
              />
            )}
          </li>
        ))}
      </ul>
      {open && (
        <div className="flex flex-col gap-2">
          <label htmlFor="evidence-text" className="font-bold">
            {t("add")}
          </label>
          <textarea
            id="evidence-text"
            rows={2}
            value={text}
            maxLength={4000}
            onChange={(event) => setText(event.target.value)}
            className="rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 py-3 outline-none"
          />
          <Button variant="secondary" disabled={!text.trim()} onClick={() => void send()}>
            {t("send")}
          </Button>
        </div>
      )}
    </section>
  );
}

/** One payment, seen by the client or by the seller. */
export function PaymentDetail({ paymentId }: { paymentId: string }) {
  const t = useTranslations("payments.detail");
  const tStatus = useTranslations("payments.status");
  const queryClient = useQueryClient();
  const key = ["payment", paymentId];
  const query = useQuery({
    queryKey: key,
    queryFn: () => getPayment(paymentId),
    // While the provider confirms a payment, look again every few seconds.
    refetchInterval: (q) => (q.state.data?.status === "pending_payment" ? 3000 : false),
  });
  const update = (payment: Payment) => queryClient.setQueryData(key, payment);

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (query.isError || !query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const payment = query.data;
  const other = payment.role === "buyer" ? payment.seller : payment.buyer;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-mention text-prune-doux font-bold">{payment.reference}</p>
        <h1 className="text-headline font-bold">{payment.description}</h1>
        <p className="bg-poudre self-start rounded-full px-3 py-1 font-bold">
          {tStatus(payment.status)}
        </p>
        {(payment.source_type === "order" || payment.source_type === "selection") &&
          payment.source_id && (
            <Link
              href={
                payment.source_type === "order"
                  ? `/orders/${payment.source_id}`
                  : `/selection/orders/${payment.source_id}`
              }
              className={buttonClasses({ variant: "secondary", className: "self-start" })}
            >
              {t("seeOrder")}
            </Link>
          )}
        <p className="flex items-center gap-2">
          <Avatar name={other.name} src={mediaSrc(other.photo, "thumb")} size="sm" />
          {payment.role === "buyer"
            ? t("soldBy", { name: other.name })
            : t("boughtBy", { name: other.name })}
        </p>
      </header>
      {payment.receipt_code && <ReceiptCode code={payment.receipt_code} />}
      {payment.status !== "pending_payment" && payment.status !== "cancelled" && (
        <Steps payment={payment} />
      )}
      <Breakdown payment={payment} />
      {payment.status === "held" && payment.role === "seller" && (
        <p className="bg-poudre rounded-2xl p-3">{t("heldForSeller")}</p>
      )}
      {payment.carrier && (
        <p>
          {payment.tracking_number
            ? t("carrier", { carrier: payment.carrier, tracking: payment.tracking_number })
            : t("carrierOnly", { carrier: payment.carrier })}
        </p>
      )}
      <DisputePanel payment={payment} onChange={update} />
      {payment.role === "seller" ? (
        <SellerActions payment={payment} onChange={update} />
      ) : (
        <BuyerActions payment={payment} onChange={update} />
      )}
    </div>
  );
}
