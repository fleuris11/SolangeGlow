"use client";

import {
  ArrowCounterClockwise,
  Camera,
  CreditCard,
  Key,
  Link as LinkIcon,
  Package,
  Truck,
  Warning,
  XCircle,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  cancelPayment,
  confirmCode,
  courierLink,
  markDelivered,
  newCode,
  openDispute,
  ship,
  startCheckout,
  type DisputeReason,
  type Payment,
} from "@/lib/api/payments";

import { sendPicture } from "./upload";

type Props = { payment: Payment; onChange: (payment: Payment) => void };

function useRun(onChange: Props["onChange"]) {
  const toast = useToast();
  const t = useTranslations("payments.actions");
  const [busy, setBusy] = useState(false);
  const run = async (step: () => Promise<Payment | void>, done?: string) => {
    setBusy(true);
    try {
      const result = await step();
      if (result) onChange(result);
      if (done) toast(done, "success");
      return true;
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, run };
}

/** The seller: ship, say it was delivered (picture), type the code, share the courier link. */
export function SellerActions({ payment, onChange }: Props) {
  const t = useTranslations("payments.actions");
  const { busy, run } = useRun(onChange);
  const [carrier, setCarrier] = useState("");
  const [tracking, setTracking] = useState("");
  const [code, setCode] = useState("");
  const proofInput = useRef<HTMLInputElement>(null);
  const can = payment.can;

  return (
    <div className="flex flex-col gap-5">
      {can.confirm && (
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void run(() => confirmCode(payment.id, code), t("released")).then(
              (ok) => ok && setCode(""),
            );
          }}
        >
          <h2 className="text-title flex items-center gap-2 font-bold">
            <Key aria-hidden size={24} weight="bold" />
            {t("codeTitle")}
          </h2>
          <p className="text-small text-prune-doux">{t("codeHelp")}</p>
          <Input
            label={t("codeLabel")}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
            hint={t("attemptsLeft", { count: payment.code_attempts_left ?? 0 })}
          />
          <Button type="submit" size="lg" disabled={busy || code.length !== 6}>
            {t("confirm")}
          </Button>
        </form>
      )}
      {/* An order of the shop is shipped from its page (with a photo of the parcel). */}
      {can.ship && payment.source_type !== "order" && (
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void run(
              () => ship(payment.id, { carrier, tracking_number: tracking }),
              t("shippedDone"),
            );
          }}
        >
          <h2 className="text-title flex items-center gap-2 font-bold">
            <Truck aria-hidden size={24} weight="bold" />
            {t("shipTitle")}
          </h2>
          <Input
            label={t("carrier")}
            value={carrier}
            onChange={(e) => setCarrier(e.target.value)}
          />
          <Input
            label={t("tracking")}
            value={tracking}
            onChange={(e) => setTracking(e.target.value)}
          />
          <Button type="submit" variant="secondary" disabled={busy}>
            <Package aria-hidden size={22} weight="bold" />
            {t("ship")}
          </Button>
        </form>
      )}
      {can.deliver && (
        <div className="flex flex-col gap-2">
          <input
            ref={proofInput}
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            tabIndex={-1}
            aria-label={t("delivered")}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (!file) return;
              void run(async () => {
                const proof = await sendPicture(file, "delivery_proof");
                return markDelivered(payment.id, proof);
              }, t("deliveredDone"));
            }}
          />
          <Button variant="secondary" disabled={busy} onClick={() => proofInput.current?.click()}>
            <Camera aria-hidden size={22} weight="bold" />
            {t("delivered")}
          </Button>
          <p className="text-small text-prune-doux">{t("deliveredHelp")}</p>
        </div>
      )}
      {can.confirm && (
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const { url } = await courierLink(payment.id);
              if (navigator.share) {
                await navigator.share({ title: payment.reference, url }).catch(() => undefined);
              } else {
                await navigator.clipboard?.writeText(url);
              }
            }, t("courierShared"))
          }
        >
          <LinkIcon aria-hidden size={22} weight="bold" />
          {t("courier")}
        </Button>
      )}
      {can.cancel && (
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() => void run(() => cancelPayment(payment.id), t("cancelled"))}
        >
          <XCircle aria-hidden size={22} weight="bold" />
          {t("cancelSale")}
        </Button>
      )}
    </div>
  );
}

const REASONS: DisputeReason[] = ["not_received", "not_as_described", "damaged", "other"];

/** The client: pay, ask for a new code, cancel before shipping, open a dispute. */
export function BuyerActions({ payment, onChange }: Props) {
  const t = useTranslations("payments.actions");
  const tReasons = useTranslations("payments.reasons");
  const { busy, run } = useRun(onChange);
  const [disputing, setDisputing] = useState(false);
  const [reason, setReason] = useState<DisputeReason | null>(null);
  const [text, setText] = useState("");
  const [photos, setPhotos] = useState<string[]>([]);
  const photoInput = useRef<HTMLInputElement>(null);
  const can = payment.can;

  const pay = () =>
    run(async () => {
      const ready = payment.checkout_url ? payment : await startCheckout(payment.id);
      window.location.assign(ready.checkout_url);
    });

  return (
    <div className="flex flex-col gap-4">
      {can.pay && (
        <Button size="lg" fullWidth disabled={busy} onClick={() => void pay()}>
          <CreditCard aria-hidden size={24} weight="bold" />
          {t("pay")}
        </Button>
      )}
      {can.new_code && (
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() => void run(() => newCode(payment.id), t("newCodeSent"))}
        >
          <ArrowCounterClockwise aria-hidden size={22} weight="bold" />
          {t("newCode")}
        </Button>
      )}
      {can.cancel && (
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() => void run(() => cancelPayment(payment.id), t("cancelled"))}
        >
          <XCircle aria-hidden size={22} weight="bold" />
          {t("cancelOrder")}
        </Button>
      )}
      {can.dispute && !disputing && (
        <Button variant="secondary" onClick={() => setDisputing(true)}>
          <Warning aria-hidden size={22} weight="bold" />
          {t("problem")}
        </Button>
      )}
      {can.dispute && disputing && (
        <form
          className="border-trait rounded-card flex flex-col gap-3 border p-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!reason) return;
            void run(
              () => openDispute(payment.id, { reason, description: text, media_ids: photos }),
              t("disputeOpened"),
            );
          }}
        >
          <h2 className="text-title font-bold">{t("problemTitle")}</h2>
          <p className="text-small text-prune-doux">{t("problemHelp")}</p>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("reason")}</legend>
            <div className="flex flex-wrap gap-2">
              {REASONS.map((value) => (
                <Chip key={value} selected={reason === value} onClick={() => setReason(value)}>
                  {tReasons(value)}
                </Chip>
              ))}
            </div>
          </fieldset>
          <label htmlFor="dispute-text" className="font-bold">
            {t("explain")}
          </label>
          <textarea
            id="dispute-text"
            rows={3}
            maxLength={4000}
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 py-3 outline-none"
          />
          <input
            ref={photoInput}
            type="file"
            accept="image/*"
            className="sr-only"
            tabIndex={-1}
            aria-label={t("addPhoto")}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (!file) return;
              void run(async () => {
                const id = await sendPicture(file, "dispute_evidence");
                setPhotos((current) => [...current, id]);
              }, t("photoAdded"));
            }}
          />
          <Button variant="quiet" disabled={busy} onClick={() => photoInput.current?.click()}>
            <Camera aria-hidden size={22} weight="bold" />
            {photos.length ? t("photos", { count: photos.length }) : t("addPhoto")}
          </Button>
          <Button type="submit" disabled={busy || !reason}>
            {t("sendDispute")}
          </Button>
        </form>
      )}
    </div>
  );
}
