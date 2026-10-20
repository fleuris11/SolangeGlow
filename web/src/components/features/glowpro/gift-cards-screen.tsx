"use client";

import { Gift, MagnifyingGlass, Plus } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  checkGiftCard,
  getGiftCards,
  getPaymentMethods,
  redeemGiftCard,
  sellGiftCard,
  type OnSiteMethod,
} from "@/lib/api/glowpro";
import { formatMoney, parseMoney } from "@/lib/money";

/** « Gift cards »: use a code at the desk, sell one at the salon, see them all. */
export function GiftCardsScreen() {
  const t = useTranslations("glowpro.giftCards");
  const locale = useLocale();
  const [q, setQ] = useState("");
  const query = useQuery({
    queryKey: ["gift-cards", q],
    queryFn: () => getGiftCards(q || undefined),
  });
  const [selling, setSelling] = useState(false);
  const rows = query.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <Gift aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} />
      </div>
      <Redeem />
      <Button variant="secondary" fullWidth onClick={() => setSelling(true)}>
        <Plus aria-hidden size={24} weight="bold" />
        {t("sell")}
      </Button>
      <Input
        label={t("search")}
        leading={<MagnifyingGlass aria-hidden size={22} />}
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<Gift size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((card) => (
            <li
              key={card.id}
              className="border-trait bg-carte rounded-card flex min-h-16 items-center gap-3 border p-3"
            >
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-bold tracking-wider">{card.code}</span>
                <span className="text-small text-prune-doux">
                  {t("for", { name: card.recipient_name })}, {t(`status.${card.status}`)}
                </span>
              </span>
              <span className="shrink-0 text-right">
                <span className="block font-bold">
                  {formatMoney(card.balance_minor, card.currency, locale)}
                </span>
                <span className="text-small text-prune-doux">
                  {t("of", { amount: formatMoney(card.amount_minor, card.currency, locale) })}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {selling && <SellSheet onClose={() => setSelling(false)} />}
    </div>
  );
}

function Redeem() {
  const t = useTranslations("glowpro.giftCards");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const [card, setCard] = useState<{
    code: string;
    balance_minor: number;
    currency: string;
  } | null>(null);
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);

  const fail = (caught: unknown) =>
    toast(caught instanceof ApiError ? caught.message : t("error"), "warning");

  const check = async () => {
    setBusy(true);
    try {
      setCard(await checkGiftCard(code));
    } catch (caught) {
      setCard(null);
      fail(caught);
    } finally {
      setBusy(false);
    }
  };

  const use = async () => {
    if (!card) return;
    const minor = parseMoney(amount, card.currency);
    if (!minor) return;
    setBusy(true);
    try {
      const after = await redeemGiftCard({ code: card.code, amount_minor: minor });
      toast(
        t("used", { balance: formatMoney(after.balance_minor, after.currency, locale) }),
        "success",
      );
      setCard(null);
      setCode("");
      setAmount("");
      await queryClient.invalidateQueries({ queryKey: ["gift-cards"] });
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="redeem" className="bg-poudre rounded-card flex flex-col gap-3 p-4">
      <h2 id="redeem" className="text-lead font-bold">
        {t("redeemTitle")}
      </h2>
      <Input
        label={t("code")}
        value={code}
        autoCapitalize="characters"
        onChange={(e) => {
          setCode(e.target.value.toUpperCase());
          setCard(null);
        }}
      />
      {!card ? (
        <Button fullWidth disabled={busy || code.trim().length < 6} onClick={() => void check()}>
          {t("check")}
        </Button>
      ) : (
        <>
          <p className="font-bold" role="status">
            {t("balance", { amount: formatMoney(card.balance_minor, card.currency, locale) })}
          </p>
          <Input
            label={t("amountToUse")}
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <Button size="lg" fullWidth disabled={busy || !amount} onClick={() => void use()}>
            {t("use")}
          </Button>
        </>
      )}
    </section>
  );
}

function SellSheet({ onClose }: { onClose: () => void }) {
  const t = useTranslations("glowpro.giftCards");
  const tMethod = useTranslations("glowpro.methods");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const methods = useQuery({ queryKey: ["salon-methods"], queryFn: getPaymentMethods });
  const [amount, setAmount] = useState("");
  const [name, setName] = useState("");
  const [method, setMethod] = useState<OnSiteMethod | "">("");
  const [busy, setBusy] = useState(false);
  const [sold, setSold] = useState<string | null>(null);

  const sell = async () => {
    const minor = parseMoney(amount, methods.data?.currency ?? "XOF");
    if (!minor || !method) return;
    setBusy(true);
    try {
      const card = await sellGiftCard({ amount_minor: minor, method, recipient_name: name });
      setSold(`${card.code} (${formatMoney(card.amount_minor, card.currency, locale)})`);
      await queryClient.invalidateQueries({ queryKey: ["gift-cards"] });
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  const available = methods.data?.methods ?? [];
  return (
    <Sheet open onOpenChange={(value) => !value && onClose()} title={t("sell")}>
      {sold ? (
        <div className="flex flex-col gap-3">
          <p className="font-bold" role="status">
            {t("soldCode", { code: sold })}
          </p>
          <Button fullWidth onClick={onClose}>
            {t("close")}
          </Button>
        </div>
      ) : available.length === 0 ? (
        <p className="text-prune-doux">{t("noMethod")}</p>
      ) : (
        <div className="flex flex-col gap-4">
          <Input
            label={t("amount")}
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <Input
            label={t("recipient")}
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
          />
          <fieldset className="flex flex-col gap-2">
            <legend className="font-bold">{t("paidWith")}</legend>
            {available.map((value) => (
              <label key={value} className="flex min-h-12 items-center gap-3">
                <input
                  type="radio"
                  name="method"
                  className="accent-hibiscus size-6"
                  checked={method === value}
                  onChange={() => setMethod(value)}
                />
                {tMethod(value)}
              </label>
            ))}
          </fieldset>
          <Button
            size="lg"
            fullWidth
            disabled={busy || !amount || !method}
            onClick={() => void sell()}
          >
            {t("sellCta")}
          </Button>
        </div>
      )}
    </Sheet>
  );
}
