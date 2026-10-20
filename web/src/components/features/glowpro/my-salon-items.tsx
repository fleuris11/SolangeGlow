"use client";

import { Gift, Stack } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getMySalonItems, payInstallment } from "@/lib/api/glowpro";
import { formatMoney } from "@/lib/money";

/** In « My appointments »: her packages (sessions left, next payment) and the gift cards
 * she offered. */
export function MySalonItems() {
  const t = useTranslations("glowpro.mine");
  const locale = useLocale();
  const toast = useToast();
  const query = useQuery({ queryKey: ["salon-mine"], queryFn: getMySalonItems });
  const [busy, setBusy] = useState(false);
  const data = query.data;
  if (!data || (data.packages.length === 0 && data.gift_cards.length === 0)) return null;

  const pay = async (id: string) => {
    setBusy(true);
    try {
      const answer = await payInstallment(id);
      window.location.assign(answer.checkout_url);
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {data.packages.length > 0 && (
        <section aria-labelledby="my-packages" className="flex flex-col gap-2">
          <h2 id="my-packages" className="text-title flex items-center gap-2 font-bold">
            <Stack aria-hidden size={26} weight="duotone" className="text-hibiscus" />
            {t("packages")}
          </h2>
          <ul className="flex flex-col gap-2">
            {data.packages.map((sold) => {
              const next = sold.installments.find((i) => i.status === "due");
              return (
                <li
                  key={sold.id}
                  className="border-trait rounded-card flex flex-col gap-2 border p-3"
                >
                  <span className="font-bold">{sold.name}</span>
                  <span className="text-small">{sold.pro_name}</span>
                  <span className="text-small text-prune-doux">
                    {t("left", { count: sold.sessions_total - sold.sessions_used })}
                  </span>
                  {next && (
                    <Button variant="secondary" disabled={busy} onClick={() => void pay(next.id)}>
                      {t("payNext", {
                        amount: formatMoney(next.amount_minor, sold.currency, locale),
                      })}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
      {data.gift_cards.length > 0 && (
        <section aria-labelledby="my-gifts" className="flex flex-col gap-2">
          <h2 id="my-gifts" className="text-title flex items-center gap-2 font-bold">
            <Gift aria-hidden size={26} weight="duotone" className="text-hibiscus" />
            {t("giftCards")}
          </h2>
          <ul className="flex flex-col gap-2">
            {data.gift_cards.map((card) => (
              <li
                key={card.id}
                className="border-trait rounded-card flex flex-col gap-1 border p-3"
              >
                <span className="font-bold tracking-wider">{card.code}</span>
                <span className="text-small">
                  {t("giftLine", {
                    name: card.recipient_name,
                    pro: card.pro_name,
                    amount: formatMoney(card.balance_minor, card.currency, locale),
                  })}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
