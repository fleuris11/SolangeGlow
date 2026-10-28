"use client";

import { Sparkle } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { checkGlowCard, payWithGlowCard } from "@/lib/api/gifts";
import { formatMoney } from "@/lib/money";

type Target = { paymentId: string } | { groupId: string };

/**
 * « I have a Glow gift card »: the card pays the whole purchase (in FCFA, in Benin).
 * `prepare` creates what is paid (a cart becomes orders) right before paying.
 */
export function GlowCardPay({
  target,
  prepare,
  onPaid,
}: {
  target?: Target;
  prepare?: () => Promise<Target>;
  onPaid: (target: Target) => void;
}) {
  const t = useTranslations("gifts.card");
  const locale = useLocale();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [balance, setBalance] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <Button variant="secondary" fullWidth onClick={() => setOpen(true)}>
        <Sparkle aria-hidden size={24} />
        {t("have")}
      </Button>
    );
  }
  return (
    <section
      aria-labelledby="glow-card-title"
      className="border-trait rounded-card flex flex-col gap-3 border p-4"
    >
      <h2 id="glow-card-title" className="text-lead flex items-center gap-2 font-bold">
        <Sparkle aria-hidden size={24} weight="duotone" className="text-hibiscus" />
        {t("title")}
      </h2>
      <Input
        label={t("code")}
        value={code}
        autoCapitalize="characters"
        autoComplete="off"
        maxLength={20}
        hint={t("hint")}
        onChange={(event) => {
          setCode(event.target.value);
          setBalance(null);
        }}
      />
      {balance && (
        <p aria-live="polite" className="bg-poudre rounded-2xl p-3 font-bold">
          {t("left", { amount: balance })}
        </p>
      )}
      {balance ? (
        <Button
          size="lg"
          fullWidth
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const what = target ?? (await prepare!());
              await payWithGlowCard({
                code: code.trim(),
                ...("groupId" in what
                  ? { group_id: what.groupId }
                  : { payment_id: what.paymentId }),
              });
              onPaid(what);
            })
          }
        >
          <Sparkle aria-hidden size={24} weight="bold" />
          {t("pay")}
        </Button>
      ) : (
        <Button
          fullWidth
          disabled={busy || code.trim().length < 6}
          onClick={() =>
            void run(async () => {
              const card = await checkGlowCard(code.trim());
              setBalance(formatMoney(card.balance.amount_minor, card.balance.currency, locale));
            })
          }
        >
          {t("check")}
        </Button>
      )}
    </section>
  );
}
