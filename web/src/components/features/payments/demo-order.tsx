"use client";

import { Flask } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CLIENT_HEADER } from "@/lib/api/client";
import { useRouter } from "@/lib/i18n/navigation";

/** Development only: a pretend order, to try the secure payment before the shop exists. */
export function DemoOrder() {
  const t = useTranslations("payments.demo");
  const router = useRouter();
  const [slug, setSlug] = useState("aicha");
  const [amount, setAmount] = useState("10000");
  const [error, setError] = useState<string>();

  const create = async () => {
    setError(undefined);
    const response = await fetch("/api/v1/dev/payments", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...CLIENT_HEADER },
      body: JSON.stringify({
        seller_slug: slug,
        items_minor: Number(amount),
        delivery_minor: 1000,
        description: t("item"),
      }),
    });
    if (!response.ok) {
      setError(t("error"));
      return;
    }
    const payment = (await response.json()) as { id: string };
    router.push(`/pay/test/${payment.id}`);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-or text-sur-or rounded-card flex gap-3 p-4">
        <Flask aria-hidden size={28} weight="fill" className="shrink-0" />
        <p className="font-bold">{t("banner")}</p>
      </div>
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <Input label={t("seller")} value={slug} onChange={(event) => setSlug(event.target.value)} />
      <Input
        label={t("amount")}
        inputMode="numeric"
        value={amount}
        error={error}
        onChange={(event) => setAmount(event.target.value.replace(/\D/g, ""))}
      />
      <Button size="lg" disabled={!slug || !amount} onClick={() => void create()}>
        {t("create")}
      </Button>
    </div>
  );
}
