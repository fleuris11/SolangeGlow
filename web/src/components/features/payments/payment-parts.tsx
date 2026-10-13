"use client";

import { CheckCircle, Circle, ShieldCheck } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";

import { SpeakButton } from "@/components/ui/speak-button";
import type { Payment } from "@/lib/api/payments";
import { cn } from "@/lib/cn";
import { formatMoney } from "@/lib/money";

/** Amounts, line by line: what the client paid; for the seller, commission and net. */
export function Breakdown({ payment }: { payment: Payment }) {
  const t = useTranslations("payments.breakdown");
  const locale = useLocale();
  const money = (value: number) => formatMoney(value, payment.currency, locale);
  const rows: [string, string, boolean?][] = [
    [t("items"), money(payment.items_minor)],
    ...(payment.delivery_minor
      ? [[t("delivery"), money(payment.delivery_minor)] as [string, string]]
      : []),
    [t("protection"), money(payment.buyer_fee_minor)],
    [t("total"), money(payment.total_minor), true],
  ];
  if (payment.role === "seller" && payment.seller_net_minor !== null) {
    rows.push([t("commission"), t("minus", { amount: money(payment.commission_minor ?? 0) })]);
    rows.push([t("net"), money(payment.seller_net_minor), true]);
  }
  if (payment.refunded_minor) rows.push([t("refunded"), money(payment.refunded_minor), true]);
  return (
    <div className="border-trait rounded-card flex flex-col gap-2 border p-4">
      <dl className="flex flex-col gap-2">
        {rows.map(([label, value, strong]) => (
          <div key={label} className={cn("flex justify-between gap-4", strong && "font-bold")}>
            <dt>{label}</dt>
            <dd className="text-right">{value}</dd>
          </div>
        ))}
      </dl>
      {payment.role === "buyer" && (
        <p className="text-small text-prune-doux mt-1">{t("protectionHelp")}</p>
      )}
    </div>
  );
}

const ORDER_STEPS = ["paid", "shipped", "received"] as const;

/** Where the order is: paid (money held), shipped, received (money to the seller). */
export function Steps({ payment }: { payment: Payment }) {
  const t = useTranslations("payments.steps");
  const service = payment.delivery_mode === "service";
  const steps = service ? (["paid", "received"] as const) : ORDER_STEPS;
  const done = {
    paid: !!payment.paid_at,
    shipped: !!payment.shipped_at,
    received: payment.status === "released",
  };
  return (
    <ol className="flex flex-col gap-2" aria-label={t("label")}>
      {steps.map((step) => (
        <li key={step} className="flex items-center gap-2">
          {done[step] ? (
            <CheckCircle aria-hidden size={24} weight="fill" className="text-feuille" />
          ) : (
            <Circle aria-hidden size={24} className="text-prune-doux" />
          )}
          <span className={cn(done[step] ? "font-bold" : "text-prune-doux")}>
            {t(service && step === "received" ? "done" : step)}
          </span>
          <span className="sr-only">{done[step] ? t("yes") : t("no")}</span>
        </li>
      ))}
    </ol>
  );
}

/** The receipt code, big and readable, with how to use it. */
export function ReceiptCode({ code }: { code: string }) {
  const t = useTranslations("payments.code");
  const spaced = `${code.slice(0, 3)} ${code.slice(3)}`;
  return (
    <section
      aria-labelledby="receipt-code"
      className="bg-poudre rounded-card flex flex-col items-center gap-3 p-5 text-center"
    >
      <h2 id="receipt-code" className="flex items-center gap-2 font-bold">
        <ShieldCheck aria-hidden size={24} weight="fill" className="text-hibiscus" />
        {t("title")}
      </h2>
      <p
        className="font-display text-display font-black tracking-widest"
        aria-label={code.split("").join(" ")}
      >
        {spaced}
      </p>
      <p className="text-small">{t("help")}</p>
      <SpeakButton text={`${t("title")}. ${code.split("").join(" ")}. ${t("help")}`} />
    </section>
  );
}
