"use client";

import { CashRegister, FilePdf, Gift } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import type { Appointment } from "@/lib/api/booking";
import { ApiError } from "@/lib/api/client";
import {
  getOnSitePayments,
  getPaymentMethods,
  invoiceOf,
  receiptOf,
  recordPayment,
  redeemGiftCard,
  type OnSiteMethod,
} from "@/lib/api/glowpro";
import { cn } from "@/lib/cn";
import { formatMoney, parseMoney } from "@/lib/money";

/** At the end of the appointment: take the money (cash, MoMo, gift card) and the invoice. */
export function CheckoutPanel({ appointment }: { appointment: Appointment }) {
  const t = useTranslations("glowpro.checkout");
  const tMethod = useTranslations("glowpro.methods");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = ["on-site", appointment.id];
  const paid = useQuery({
    queryKey: key,
    queryFn: () => getOnSitePayments({ appointment: appointment.id }),
  });
  const methods = useQuery({ queryKey: ["salon-methods"], queryFn: getPaymentMethods });
  const currency = appointment.currency;
  const already =
    (paid.data ?? []).filter((p) => !p.cancelled).reduce((sum, p) => sum + p.amount_minor, 0) +
    (appointment.payment?.status === "held" || appointment.payment?.status === "released"
      ? appointment.deposit_minor
      : 0);
  const due = Math.max(0, (appointment.price_minor ?? 0) - already);
  const [method, setMethod] = useState<OnSiteMethod | "">("");
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  const fail = (caught: unknown) =>
    toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
  const refresh = () => queryClient.invalidateQueries({ queryKey: key });

  const take = async () => {
    const minor = amount ? parseMoney(amount, currency) : due;
    if (!minor || !method) return;
    setBusy(true);
    try {
      const payment = await recordPayment({
        amount_minor: minor,
        method,
        appointment_id: appointment.id,
        reference,
      });
      toast(t("taken", { amount: formatMoney(minor, currency, locale) }), "success");
      const receipt = await receiptOf(payment.id);
      window.open(receipt.pdf_url, "_blank", "noopener");
      setAmount("");
      setReference("");
      await refresh();
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  };

  const redeemCard = async () => {
    const minor = amount ? parseMoney(amount, currency) : due;
    if (!minor) return;
    setBusy(true);
    try {
      const card = await redeemGiftCard({
        code,
        amount_minor: minor,
        appointment_id: appointment.id,
      });
      toast(
        t("cardUsed", { balance: formatMoney(card.balance_minor, card.currency, locale) }),
        "success",
      );
      setCode("");
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  };

  const invoice = async () => {
    setBusy(true);
    try {
      const document = await invoiceOf(appointment.id);
      window.open(document.pdf_url, "_blank", "noopener");
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  };

  const available = methods.data?.methods ?? [];
  return (
    <section
      aria-labelledby="checkout"
      className="border-trait rounded-card flex flex-col gap-3 border p-4"
    >
      <h3 id="checkout" className="flex items-center gap-2 font-bold">
        <CashRegister aria-hidden size={24} weight="duotone" className="text-hibiscus" />
        {t("title")}
      </h3>
      <p className="text-small">
        {t("summary", {
          paid: formatMoney(already, currency, locale),
          due: formatMoney(due, currency, locale),
        })}
      </p>
      {available.length > 0 ? (
        <>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t("how")}>
            {available.map((value) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={method === value}
                onClick={() => setMethod(value)}
                className={cn(
                  "min-h-12 rounded-full border-2 px-4 font-bold",
                  method === value
                    ? "border-hibiscus bg-hibiscus text-sur-hibiscus"
                    : "border-trait",
                )}
              >
                {tMethod(value)}
              </button>
            ))}
          </div>
          <Input
            label={t("amount")}
            hint={t("amountHint", { due: formatMoney(due, currency, locale) })}
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          {method === "momo" && (
            <Input
              label={t("reference")}
              value={reference}
              maxLength={60}
              onChange={(e) => setReference(e.target.value)}
            />
          )}
          <Button
            fullWidth
            disabled={busy || !method || (!amount && !due)}
            onClick={() => void take()}
          >
            {t("take")}
          </Button>
        </>
      ) : (
        <p className="text-small text-prune-doux">{t("noMethod")}</p>
      )}
      <p className="text-small text-prune-doux">{t("notCertified")}</p>
      <div className="flex items-end gap-2">
        <Input
          className="flex-1"
          label={t("giftCard")}
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
        />
        <Button
          variant="secondary"
          disabled={busy || code.length < 6}
          onClick={() => void redeemCard()}
        >
          <Gift aria-hidden size={22} />
          {t("useCard")}
        </Button>
      </div>
      {appointment.status === "completed" && (
        <Button variant="quiet" fullWidth disabled={busy} onClick={() => void invoice()}>
          <FilePdf aria-hidden size={22} />
          {t("invoice")}
        </Button>
      )}
    </section>
  );
}
