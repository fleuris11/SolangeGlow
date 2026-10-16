"use client";

import { Camera, CheckCircle, Hourglass, MagnifyingGlass } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getMedia } from "@/lib/api/payments";
import {
  declineQuote,
  getPickupPoints,
  getRequests,
  orderQuote,
  sendRequest,
  uploadRequestPhoto,
  type SelectionRequest,
} from "@/lib/api/selection";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

import { shortDate } from "./dates";

async function sendPhoto(file: Blob): Promise<string> {
  const sent = await uploadRequestPhoto(file);
  for (let attempt = 0; attempt < 40; attempt++) {
    const media = await getMedia(sent.id);
    if (media.status === "ready") return media.id;
    if (media.status === "rejected" || media.status === "failed") throw new Error("refused");
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error("timeout");
}

/** A quote: price per shipping mode, the pick-up point, then payment. */
function Quote({ request, onChange }: { request: SelectionRequest; onChange: () => void }) {
  const t = useTranslations("selection.requests");
  const locale = useLocale();
  const toast = useToast();
  const points = useQuery({ queryKey: ["selection-points"], queryFn: getPickupPoints });
  const [mode, setMode] = useState<"grouped" | "express">("grouped");
  const [point, setPoint] = useState("");
  const [busy, setBusy] = useState(false);
  const chosenPoint = point || points.data?.[0]?.id || "";
  const money = (value: number) => formatMoney(value, "XOF", locale);
  const estimate = mode === "express" ? request.estimates.express : request.estimates.grouped;
  const price = mode === "express" ? request.express_price_xof : request.price_xof;

  const pay = async () => {
    setBusy(true);
    try {
      const order = await orderQuote(request.id, {
        shipping_mode: mode,
        pickup_point_id: chosenPoint,
      });
      window.location.assign(order.payment?.checkout_url || `/selection/orders/${order.id}`);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-lead font-bold">{request.title}</p>
      {request.valid_until && (
        <p className="text-small text-prune-doux">
          {t("validUntil", { date: shortDate(request.valid_until, locale) })}
        </p>
      )}
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">{t("shipping")}</legend>
        {(["grouped", "express"] as const)
          .filter((value) => value === "grouped" || request.express_price_xof !== null)
          .map((value) => (
            <label
              key={value}
              className={cn(
                "flex min-h-14 items-center gap-3 rounded-2xl border-2 px-4",
                mode === value ? "border-hibiscus bg-poudre" : "border-trait",
              )}
            >
              <input
                type="radio"
                name={`mode-${request.id}`}
                className="sr-only"
                checked={mode === value}
                onChange={() => setMode(value)}
              />
              <span className="flex-1 font-bold">{t(value)}</span>
              <span className="font-bold">
                {money((value === "express" ? request.express_price_xof : request.price_xof) ?? 0)}
              </span>
            </label>
          ))}
      </fieldset>
      <label className="flex flex-col gap-2 font-bold">
        {t("pickup")}
        <select
          value={chosenPoint}
          onChange={(event) => setPoint(event.target.value)}
          className="rounded-field bg-poudre min-h-14 px-4"
        >
          {(points.data ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name} ({item.city})
            </option>
          ))}
        </select>
      </label>
      <p className="text-small text-prune-doux">
        {t("between", {
          from: shortDate(estimate.from, locale),
          to: shortDate(estimate.to, locale),
        })}
      </p>
      <Button size="lg" fullWidth disabled={busy || !chosenPoint} onClick={() => void pay()}>
        {t("pay", { amount: money(price ?? 0) })}
      </Button>
      <Button
        variant="quiet"
        disabled={busy}
        onClick={() =>
          void declineQuote(request.id)
            .then(onChange)
            .catch(() => toast(t("error"), "warning"))
        }
      >
        {t("decline")}
      </Button>
    </div>
  );
}

/** « Find me this »: a link or a photo, then a quote to pay. */
export function SpecialRequests() {
  const t = useTranslations("selection.requests");
  const tStatus = useTranslations("selection.requestStatus");
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["selection-requests"], queryFn: getRequests });
  const [link, setLink] = useState("");
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const photoInput = useRef<HTMLInputElement>(null);
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["selection-requests"] });

  const submit = async () => {
    setBusy(true);
    try {
      await sendRequest({ link: link.trim(), note: note.trim(), photo });
      setLink("");
      setNote("");
      setPhoto(null);
      toast(t("sent"), "success");
      refresh();
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
            <MagnifyingGlass aria-hidden size={28} weight="duotone" className="text-hibiscus" />
            {t("title")}
          </h1>
          <SpeakButton text={`${t("title")}. ${t("help")}`} />
        </div>
        <p>{t("help")}</p>
      </header>

      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <Input
          label={t("link")}
          type="url"
          inputMode="url"
          value={link}
          maxLength={500}
          onChange={(event) => setLink(event.target.value)}
        />
        <input
          ref={photoInput}
          type="file"
          accept="image/*"
          className="sr-only"
          tabIndex={-1}
          aria-label={t("photo")}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            setBusy(true);
            sendPhoto(file)
              .then((id) => {
                setPhoto(id);
                toast(t("photoAdded"), "success");
              })
              .catch(() => toast(t("photoError"), "warning"))
              .finally(() => setBusy(false));
          }}
        />
        <Button variant="secondary" disabled={busy} onClick={() => photoInput.current?.click()}>
          {photo ? (
            <CheckCircle aria-hidden size={22} weight="fill" className="text-feuille" />
          ) : (
            <Camera aria-hidden size={22} weight="bold" />
          )}
          {photo ? t("photoOk") : t("photo")}
        </Button>
        <label htmlFor="request-note" className="font-bold">
          {t("note")}
        </label>
        <textarea
          id="request-note"
          rows={3}
          maxLength={1000}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          className="rounded-field bg-poudre focus:border-hibiscus w-full border-2 border-transparent px-4 py-3 outline-none"
        />
        <Button type="submit" size="lg" fullWidth disabled={busy || (!link.trim() && !photo)}>
          {t("send")}
        </Button>
      </form>

      <section aria-labelledby="my-requests" className="flex flex-col gap-3">
        <h2 id="my-requests" className="text-title font-bold">
          {t("mine")}
        </h2>
        {query.isPending ? (
          <Skeleton className="h-32 rounded-2xl" />
        ) : (query.data ?? []).length === 0 ? (
          <p className="text-prune-doux">{t("none")}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {(query.data ?? []).map((request) => (
              <li
                key={request.id}
                className="border-trait rounded-card flex flex-col gap-3 border p-4"
              >
                <div className="flex gap-3">
                  {request.photo && (
                    // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                    <img
                      src={mediaSrc(request.photo, "thumb")}
                      alt=""
                      className="bg-poudre size-16 shrink-0 rounded-xl object-cover"
                    />
                  )}
                  <div className="flex min-w-0 flex-col gap-1">
                    <span className="text-small bg-poudre self-start rounded-full px-3 py-1 font-bold">
                      {request.status === "new" && (
                        <Hourglass aria-hidden size={14} className="mr-1 inline" />
                      )}
                      {tStatus(request.status)}
                    </span>
                    {request.link && <span className="text-small truncate">{request.link}</span>}
                    {request.note && (
                      <span className="text-small text-prune-doux">{request.note}</span>
                    )}
                  </div>
                </div>
                {request.answer && <p className="bg-poudre rounded-2xl p-3">{request.answer}</p>}
                {request.status === "quoted" && <Quote request={request} onChange={refresh} />}
                {request.order_id && (
                  <Link
                    href={`/selection/orders/${request.order_id}`}
                    className={buttonClasses({ variant: "secondary" })}
                  >
                    {t("seeOrder")}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
