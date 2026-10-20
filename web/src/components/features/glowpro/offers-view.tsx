"use client";

import { Gift, Stack } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError, hasSession } from "@/lib/api/client";
import { buyGiftCard, buyPackage, getOffers } from "@/lib/api/glowpro";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { cn } from "@/lib/cn";
import { usePathname, useRouter } from "@/lib/i18n/navigation";
import { formatMoney, parseMoney } from "@/lib/money";

const subscribeNothing = () => () => {};

/** A gift card (amount, for whom, a message) and the packages of a salon. */
export function OffersView({ slug }: { slug: string }) {
  const t = useTranslations("glowpro.offers");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const signedIn = useSyncExternalStore(subscribeNothing, hasSession, () => false);
  const query = useQuery({ queryKey: ["offers", slug], queryFn: () => getOffers(slug) });
  const [amount, setAmount] = useState<number | null>(null);
  const [custom, setCustom] = useState("");
  const [recipient, setRecipient] = useState("");
  const [contact, setContact] = useState("");
  const [message, setMessage] = useState("");
  const [from, setFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const [times, setTimes] = useState<Record<string, number>>({});

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  const offer = query.data?.gift_cards;
  const packages = query.data?.packages ?? [];
  const currency = offer?.currency ?? "XOF";
  const chosen = custom ? parseMoney(custom, currency) : amount;

  const signIn = () => {
    rememberReturnPath(pathname);
    router.push("/auth?as=client");
  };

  const pay = async (action: () => Promise<{ checkout_url: string }>) => {
    if (!signedIn) {
      signIn();
      return;
    }
    setBusy(true);
    try {
      const answer = await action();
      window.location.assign(answer.checkout_url);
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      {offer && (
        <section aria-labelledby="gift" className="flex flex-col gap-4">
          <h2 id="gift" className="text-title flex items-center gap-2 font-bold">
            <Gift aria-hidden size={28} weight="duotone" className="text-hibiscus" />
            {t("giftTitle")}
          </h2>
          <p className="text-prune-doux">{t("giftHelp", { days: offer.validity_days })}</p>
          <div role="radiogroup" aria-label={t("amount")} className="flex flex-wrap gap-2">
            {offer.suggestions.map((value) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={!custom && amount === value}
                onClick={() => {
                  setAmount(value);
                  setCustom("");
                }}
                className={cn(
                  "min-h-12 rounded-full border-2 px-4 font-bold",
                  !custom && amount === value
                    ? "border-hibiscus bg-hibiscus text-sur-hibiscus"
                    : "border-trait",
                )}
              >
                {formatMoney(value, currency, locale)}
              </button>
            ))}
          </div>
          <Input
            label={t("otherAmount")}
            hint={t("limits", {
              min: formatMoney(offer.min_minor, currency, locale),
              max: formatMoney(offer.max_minor, currency, locale),
            })}
            inputMode="decimal"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
          />
          <Input
            label={t("recipient")}
            value={recipient}
            maxLength={80}
            onChange={(e) => setRecipient(e.target.value)}
          />
          <Input
            label={t("contact")}
            hint={t("contactHint")}
            value={contact}
            maxLength={120}
            onChange={(e) => setContact(e.target.value)}
          />
          <Input
            label={t("message")}
            value={message}
            maxLength={300}
            onChange={(e) => setMessage(e.target.value)}
          />
          <Input
            label={t("from")}
            value={from}
            maxLength={80}
            onChange={(e) => setFrom(e.target.value)}
          />
          <Button
            size="lg"
            fullWidth
            disabled={busy || !chosen || !recipient.trim()}
            onClick={() =>
              void pay(() =>
                buyGiftCard(slug, {
                  amount_minor: chosen ?? 0,
                  recipient_name: recipient,
                  recipient_contact: contact,
                  message,
                  from_name: from,
                }),
              )
            }
          >
            {signedIn
              ? t("payGift", { amount: chosen ? formatMoney(chosen, currency, locale) : "" })
              : t("signIn")}
          </Button>
        </section>
      )}

      {packages.length > 0 && (
        <section aria-labelledby="packages" className="flex flex-col gap-4">
          <h2 id="packages" className="text-title flex items-center gap-2 font-bold">
            <Stack aria-hidden size={28} weight="duotone" className="text-hibiscus" />
            {t("packagesTitle")}
          </h2>
          <ul className="flex flex-col gap-3">
            {packages.map((p) => {
              const count = times[p.id] ?? 1;
              return (
                <li
                  key={p.id}
                  className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-bold">{p.name}</span>
                    <span className="font-bold">
                      {formatMoney(p.price_minor, p.currency, locale)}
                    </span>
                  </div>
                  <span className="text-small text-prune-doux">
                    {t("packageLine", { sessions: p.sessions, service: p.service_name })}
                  </span>
                  {p.max_installments > 1 && (
                    <label className="flex flex-col gap-2 font-bold">
                      {t("times")}
                      <select
                        value={count}
                        onChange={(e) => setTimes({ ...times, [p.id]: Number(e.target.value) })}
                        className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
                      >
                        {Array.from({ length: p.max_installments }, (_, i) => i + 1).map((n) => (
                          <option key={n} value={n}>
                            {t("timesValue", { count: n })}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  <Button
                    fullWidth
                    disabled={busy}
                    onClick={() => void pay(() => buyPackage(slug, p.id, count))}
                  >
                    {signedIn
                      ? t("payPackage", {
                          amount: formatMoney(
                            p.price_minor - Math.floor(p.price_minor / count) * (count - 1),
                            p.currency,
                            locale,
                          ),
                        })
                      : t("signIn")}
                  </Button>
                  <p className="text-small text-prune-doux">{t("packageRule")}</p>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
