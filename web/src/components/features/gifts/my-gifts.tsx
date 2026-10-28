"use client";

import {
  ArrowCounterClockwise,
  CheckCircle,
  Circle,
  Copy,
  Gift,
  LockKey,
  PaperPlaneTilt,
  ShareNetwork,
  Sparkle,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  cancelGift,
  getReceivedGifts,
  getSentGift,
  getSentGifts,
  payGiftAgain,
  resendGift,
  type GiftSent,
} from "@/lib/api/gifts";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

function Thumb({ gift }: { gift: { photo: GiftSent["photo"]; pro: GiftSent["pro"] } }) {
  const src = mediaSrc(gift.photo ?? gift.pro?.photo, "thumb");
  return src ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="" className="petal size-14 shrink-0 object-cover" loading="lazy" />
  ) : (
    <span className="bg-poudre text-hibiscus petal inline-flex size-14 shrink-0 items-center justify-center">
      <Gift aria-hidden size={28} weight="duotone" />
    </span>
  );
}

/** « My gifts »: those sent (with their follow-up), and the Glow gift cards received. */
export function MyGifts() {
  const t = useTranslations("gifts.mine");
  const tStatus = useTranslations("gifts.status");
  const locale = useLocale();
  const [tab, setTab] = useState<"sent" | "received">("sent");
  const sent = useQuery({ queryKey: ["gifts-sent"], queryFn: getSentGifts });
  const received = useQuery({ queryKey: ["gifts-received"], queryFn: getReceivedGifts });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={t("title")} />
      </div>
      <Link href="/offrir" className={buttonClasses({ size: "lg", fullWidth: true })}>
        <Gift aria-hidden size={24} weight="bold" />
        {t("offer")}
      </Link>
      <div role="tablist" className="bg-poudre grid grid-cols-2 gap-1 rounded-full p-1">
        {(["sent", "received"] as const).map((value) => (
          <button
            key={value}
            role="tab"
            type="button"
            aria-selected={tab === value}
            onClick={() => setTab(value)}
            className={cn(
              "min-h-12 rounded-full font-bold",
              tab === value ? "bg-carte text-prune" : "text-prune-doux",
            )}
          >
            {t(value)}
          </button>
        ))}
      </div>

      {tab === "sent" && (
        <div role="tabpanel" className="flex flex-col gap-3">
          {sent.isPending && <Skeleton className="rounded-card h-40" />}
          {sent.data?.length === 0 && (
            <EmptyState
              icon={<Gift size={48} weight="duotone" />}
              title={t("noneSent")}
              description={t("noneSentHelp")}
            />
          )}
          <ul className="flex flex-col gap-3">
            {sent.data?.map((gift) => (
              <li key={gift.id}>
                <Link
                  href={`/cadeaux/${gift.id}`}
                  className="border-trait bg-carte rounded-card flex items-center gap-3 border p-3"
                >
                  <Thumb gift={gift} />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate font-bold">{gift.title}</span>
                    <span className="text-small text-prune-doux">
                      {t("for", { name: gift.recipient_name })}
                    </span>
                    <span className="text-small font-bold">{tStatus(gift.status)}</span>
                  </span>
                  {gift.paid && (
                    <span className="font-bold">
                      {formatMoney(gift.paid.amount_minor, gift.paid.currency, locale)}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "received" && (
        <div role="tabpanel" className="flex flex-col gap-3">
          {received.isPending && <Skeleton className="rounded-card h-40" />}
          {received.data?.length === 0 && (
            <EmptyState icon={<Sparkle size={48} weight="duotone" />} title={t("noneReceived")} />
          )}
          <ul className="flex flex-col gap-3">
            {received.data?.map((gift) => (
              <li key={gift.id}>
                <Link
                  href={`/cadeau/${gift.token}`}
                  className="border-trait bg-carte rounded-card flex items-center gap-3 border p-3"
                >
                  <Thumb gift={gift} />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate font-bold">{gift.title}</span>
                    <span className="text-small text-prune-doux">
                      {t("from", { name: gift.from_name })}
                    </span>
                    {gift.code && (
                      <span className="text-small font-bold tracking-widest">{gift.code}</span>
                    )}
                  </span>
                  <span className="font-bold">
                    {formatMoney(gift.balance.amount_minor, gift.balance.currency, locale)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** One sent gift: its steps, the link to share, the photo of the result, cancel. */
export function SentGiftDetail({ id, justPaid }: { id: string; justPaid: boolean }) {
  const t = useTranslations("gifts.detail");
  const tStatus = useTranslations("gifts.status");
  const tSteps = useTranslations("gifts.steps");
  const tUse = useTranslations("gifts.useStatus");
  const locale = useLocale();
  const toast = useToast();
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const query = useQuery({ queryKey: ["gift-sent", id], queryFn: () => getSentGift(id) });

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const gift = query.data;
  if (!gift) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const money = (value: { amount_minor: number; currency: string }) =>
    formatMoney(value.amount_minor, value.currency, locale);
  const date = (iso: string) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
      new Date(iso),
    );
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
  const update = (fresh: GiftSent) => client.setQueryData(["gift-sent", id], fresh);
  const shareText = t("shareText", { name: gift.recipient_name, link: gift.link });
  const paidNow = justPaid && ["scheduled", "sent"].includes(gift.status);

  return (
    <div className="flex flex-col gap-6">
      {paidNow && (
        <div className="flex flex-col items-center gap-3 text-center">
          <Bloom label={t("paid")} />
          <p className="font-display text-headline font-black">{t("paid")}</p>
          <p>
            {gift.status === "scheduled"
              ? t("paidLater", {
                  date: new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                    new Date(gift.send_at),
                  ),
                })
              : t("paidNow", { name: gift.recipient_name })}
          </p>
        </div>
      )}
      <header className="flex flex-col gap-2">
        <p className="text-mention text-prune-doux font-bold">{gift.reference}</p>
        <h1 className="text-headline font-bold">{gift.title}</h1>
        <p>{t("for", { name: gift.recipient_name })}</p>
        <p className="bg-poudre self-start rounded-full px-3 py-1 font-bold">
          {tStatus(gift.status)}
        </p>
      </header>

      {gift.status === "waiting_payment" && (
        <Button
          size="lg"
          fullWidth
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const result = await payGiftAgain(id);
              window.location.assign(result.checkout_url);
            })
          }
        >
          <LockKey aria-hidden size={24} />
          {t("pay", { amount: gift.paid ? money(gift.paid) : "" })}
        </Button>
      )}

      {gift.status !== "waiting_payment" && (
        <ol className="flex flex-col gap-3" aria-label={t("steps")}>
          {gift.steps.map((step) => (
            <li key={step.key} className="flex items-center gap-3">
              {step.at ? (
                <CheckCircle aria-hidden size={28} weight="fill" className="text-feuille" />
              ) : (
                <Circle aria-hidden size={28} className="text-trait" />
              )}
              <span className={cn("flex-1", step.at ? "font-bold" : "text-prune-doux")}>
                {tSteps(step.key)}
              </span>
              {step.at && <span className="text-small">{date(step.at)}</span>}
            </li>
          ))}
        </ol>
      )}

      {gift.proof && (
        <figure className="flex flex-col gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={mediaSrc(gift.proof, "medium", "large")}
            alt={t("proofAlt", { name: gift.recipient_name })}
            className="rounded-card aspect-square w-full object-cover"
          />
          <figcaption className="font-bold">{t("proof", { name: gift.recipient_name })}</figcaption>
        </figure>
      )}

      {gift.can_resend && (
        <section aria-labelledby="share-title" className="flex flex-col gap-3">
          <h2 id="share-title" className="text-title font-bold">
            {t("shareTitle")}
          </h2>
          <p className="text-small text-prune-doux">{t("shareHelp")}</p>
          <a
            href={`https://wa.me/?text=${encodeURIComponent(shareText)}`}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClasses({ fullWidth: true })}
          >
            <ShareNetwork aria-hidden size={24} />
            {t("whatsapp")}
          </a>
          <div className="flex flex-col gap-3">
            <Button
              variant="secondary"
              onClick={() =>
                void navigator.clipboard
                  ?.writeText(gift.link)
                  .then(() => toast(t("copied"), "success"))
              }
            >
              <Copy aria-hidden size={20} />
              {t("copy")}
            </Button>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  update(await resendGift(id));
                  toast(t("resent", { name: gift.recipient_name }), "success");
                })
              }
            >
              <PaperPlaneTilt aria-hidden size={20} />
              {t("resend")}
            </Button>
          </div>
          {gift.code && (
            <p className="bg-poudre rounded-2xl p-3">
              {t("code")} <span className="font-bold tracking-widest">{gift.code}</span>
            </p>
          )}
        </section>
      )}

      {gift.uses.length > 0 && (
        <section aria-labelledby="uses-title" className="flex flex-col gap-2">
          <h2 id="uses-title" className="text-title font-bold">
            {t("uses")}
          </h2>
          <ul className="flex flex-col gap-2">
            {gift.uses.map((use) => (
              <li key={use.id} className="border-trait rounded-card flex flex-col gap-1 border p-3">
                <span className="font-bold">{use.label}</span>
                <span className="text-small">
                  {money(use.amount)}
                  {use.status &&
                    ` — ${tUse.has(use.status as "pending") ? tUse(use.status as "pending") : use.status}`}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <dl className="border-trait rounded-card flex flex-col gap-2 border p-4">
        {[
          [t("worth"), money(gift.value)],
          [t("price"), money(gift.price)],
          ...(gift.fee ? [[t("fee"), money(gift.fee)]] : []),
          [
            t("validUntil"),
            new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
              new Date(`${gift.expires_on}T12:00:00Z`),
            ),
          ],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4">
            <dt>{label}</dt>
            <dd className="text-right font-bold">{value}</dd>
          </div>
        ))}
      </dl>

      {gift.can_cancel && (
        <div className="flex flex-col gap-2">
          {confirming ? (
            <div className="border-alerte rounded-card flex flex-col gap-3 border-2 p-4">
              <p className="font-bold">{t("cancelConfirm")}</p>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      update(await cancelGift(id));
                      setConfirming(false);
                      toast(t("cancelled"), "success");
                    })
                  }
                >
                  {t("cancelYes")}
                </Button>
                <Button variant="secondary" onClick={() => setConfirming(false)}>
                  {t("cancelNo")}
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="quiet" onClick={() => setConfirming(true)}>
              <ArrowCounterClockwise aria-hidden size={20} />
              {t("cancel")}
            </Button>
          )}
          {gift.cancel_until && (
            <p className="text-small text-prune-doux">
              {t("cancelUntil", {
                date: new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                  new Date(gift.cancel_until),
                ),
              })}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
