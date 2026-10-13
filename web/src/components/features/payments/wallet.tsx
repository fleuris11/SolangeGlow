"use client";

import { Bank, Clock, HandCoins, Receipt, Wallet as WalletIcon } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  getTaxProfile,
  getWallet,
  getWalletHistory,
  requestPayout,
  savePayoutMethod,
  saveTaxProfile,
  type TaxProfile,
  type Wallet,
} from "@/lib/api/payments";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

const OPERATORS = ["MTN", "Moov", "Celtiis"];

function Balances({ wallet }: { wallet: Wallet }) {
  const t = useTranslations("payments.wallet");
  const locale = useLocale();
  const money = (value: number) => formatMoney(value, wallet.currency, locale);
  const cards = [
    { label: t("pending"), value: wallet.pending_minor, help: t("pendingHelp"), icon: Clock },
    {
      label: t("available"),
      value: wallet.available_minor,
      help: t("availableHelp"),
      icon: WalletIcon,
    },
    { label: t("inProgress"), value: wallet.in_progress_minor, help: "", icon: HandCoins },
    { label: t("paidOut"), value: wallet.paid_out_minor, help: "", icon: Bank },
  ];
  return (
    <ul className="grid grid-cols-2 gap-3">
      {cards.map(({ label, value, help, icon: Icon }) => (
        <li
          key={label}
          className="border-trait rounded-card flex min-w-0 flex-col gap-1 border p-3"
        >
          <span className="text-small flex items-center gap-1 font-bold">
            <Icon aria-hidden size={18} weight="bold" />
            {label}
          </span>
          <span className="font-display text-lead font-black break-words">{money(value)}</span>
          {help && <span className="text-mention text-prune-doux">{help}</span>}
        </li>
      ))}
    </ul>
  );
}

function PayoutForm({ wallet }: { wallet: Wallet }) {
  const t = useTranslations("payments.wallet");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<"mobile_money" | "fake">("mobile_money");
  const [operator, setOperator] = useState("MTN");
  const [number, setNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const enough = wallet.available_minor >= Math.max(wallet.minimum_minor, 1);

  const run = async (step: () => Promise<unknown>, done: string) => {
    setBusy(true);
    try {
      await step();
      toast(done, "success");
      await queryClient.invalidateQueries({ queryKey: ["wallet"] });
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby={`payout-${wallet.currency}`} className="flex flex-col gap-3">
      <h2 id={`payout-${wallet.currency}`} className="text-title font-bold">
        {t("payoutTitle")}
      </h2>
      {wallet.payout_method ? (
        <p>{t("payoutTo", { method: wallet.payout_method })}</p>
      ) : (
        <p className="text-prune-doux">{t("noMethod")}</p>
      )}
      <Button
        size="lg"
        disabled={busy || !enough || !wallet.payout_method}
        onClick={() =>
          void run(
            () => requestPayout(wallet.available_minor, wallet.currency),
            t("payoutRequested"),
          )
        }
      >
        <HandCoins aria-hidden size={24} weight="bold" />
        {t("payoutAll", { amount: formatMoney(wallet.available_minor, wallet.currency, locale) })}
      </Button>
      <p className="text-small text-prune-doux">
        {t("minimum", { amount: formatMoney(wallet.minimum_minor, wallet.currency, locale) })}
      </p>
      <details className="border-trait rounded-card border p-4">
        <summary className="cursor-pointer font-bold">{t("methodTitle")}</summary>
        <div className="mt-3 flex flex-col gap-3">
          <div className="flex flex-wrap gap-2" role="group" aria-label={t("methodKind")}>
            <Chip selected={kind === "mobile_money"} onClick={() => setKind("mobile_money")}>
              {t("mobileMoney")}
            </Chip>
            {process.env.NODE_ENV !== "production" && (
              <Chip selected={kind === "fake"} onClick={() => setKind("fake")}>
                {t("testAccount")}
              </Chip>
            )}
          </div>
          {kind === "mobile_money" && (
            <>
              <div className="flex flex-wrap gap-2" role="group" aria-label={t("operator")}>
                {OPERATORS.map((name) => (
                  <Chip key={name} selected={operator === name} onClick={() => setOperator(name)}>
                    {name}
                  </Chip>
                ))}
              </div>
              <Input
                label={t("number")}
                inputMode="tel"
                value={number}
                onChange={(event) => setNumber(event.target.value.replace(/[^\d+]/g, ""))}
              />
            </>
          )}
          <Button
            variant="secondary"
            disabled={busy || (kind === "mobile_money" && number.length < 8)}
            onClick={() =>
              void run(
                () =>
                  savePayoutMethod(
                    kind === "fake"
                      ? { currency: wallet.currency, kind, operator: "", number: "" }
                      : { currency: wallet.currency, kind, operator, number },
                  ),
                t("methodSaved"),
              )
            }
          >
            {t("saveMethod")}
          </Button>
        </div>
      </details>
    </section>
  );
}

function History({ currency }: { currency: string }) {
  const t = useTranslations("payments.wallet");
  const locale = useLocale();
  const query = useQuery({
    queryKey: ["wallet", "history", currency],
    queryFn: () => getWalletHistory(currency),
  });
  if (query.isPending) return <Skeleton className="h-24 rounded-2xl" />;
  const lines = query.data ?? [];
  return (
    <section aria-labelledby={`history-${currency}`} className="flex flex-col gap-2">
      <h2 id={`history-${currency}`} className="text-title font-bold">
        {t("history")}
      </h2>
      {lines.length === 0 ? (
        <p className="text-prune-doux">{t("noHistory")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {lines.map((line) => (
            <li
              key={line.id}
              className="border-trait flex items-center justify-between gap-3 border-b pb-2"
            >
              <span className="flex flex-col">
                <span className="font-bold">
                  {t(`kinds.${line.kind.replace(".", "_")}` as "kinds.payment_held")}
                </span>
                <span className="text-mention text-prune-doux">
                  {t(line.account === "pending" ? "inPending" : "inAvailable")}
                  {line.payment_id && (
                    <>
                      {" "}
                      <Link href={`/payments/${line.payment_id}`} className="underline">
                        {line.reference}
                      </Link>
                    </>
                  )}
                </span>
              </span>
              <span className="shrink-0 font-bold">
                {formatMoney(line.amount_minor, currency, locale)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function TaxForm({ initial }: { initial: TaxProfile | null }) {
  const t = useTranslations("payments.tax");
  const toast = useToast();
  const [values, setValues] = useState({
    legal_name: initial?.legal_name ?? "",
    address: initial?.address ?? "",
    postal_code: initial?.postal_code ?? "",
    city: initial?.city ?? "",
    country: initial?.country ?? "BJ",
    tax_id: "",
  });
  const field = (name: keyof typeof values, label: string, hint?: string) => (
    <Input
      label={label}
      hint={hint}
      value={values[name]}
      onChange={(event) => setValues({ ...values, [name]: event.target.value })}
    />
  );
  return (
    <details className="border-trait rounded-card border p-4">
      <summary className="flex cursor-pointer items-center gap-2 font-bold">
        <Receipt aria-hidden size={22} weight="bold" />
        {t("title")}
      </summary>
      <form
        className="mt-3 flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          saveTaxProfile(values)
            .then(() => toast(t("saved"), "success"))
            .catch((failure: unknown) =>
              toast(failure instanceof ApiError ? failure.message : t("error"), "warning"),
            );
        }}
      >
        <p className="text-small text-prune-doux">{t("help")}</p>
        {field("legal_name", t("legalName"))}
        {field("address", t("address"))}
        {field("postal_code", t("postalCode"))}
        {field("city", t("city"))}
        {field("country", t("country"))}
        {field(
          "tax_id",
          t("taxId"),
          initial?.tax_id_hint ? t("taxIdKept", { hint: initial.tax_id_hint }) : undefined,
        )}
        <Button type="submit" variant="secondary">
          {t("save")}
        </Button>
      </form>
    </details>
  );
}

/** The wallet of a pro: pending, available, payouts, history, tax data. */
export function WalletScreen() {
  const t = useTranslations("payments.wallet");
  const wallet = useQuery({ queryKey: ["wallet"], queryFn: getWallet });
  const tax = useQuery({ queryKey: ["tax-profile"], queryFn: getTaxProfile });
  if (wallet.isPending || tax.isPending) return <Skeleton className="rounded-card h-80" />;
  if (!wallet.data) {
    return (
      <p role="alert" className="font-bold">
        {t("error")}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <p className="text-prune-doux">{t("help")}</p>
      {wallet.data.wallets.map((item) => (
        <div key={item.currency} className="flex flex-col gap-6">
          <Balances wallet={item} />
          <PayoutForm wallet={item} />
          <History currency={item.currency} />
        </div>
      ))}
      <Link href="/payments?role=seller" className="text-hibiscus font-bold underline">
        {t("sales")}
      </Link>
      <TaxForm initial={tax.data ?? null} />
    </div>
  );
}
