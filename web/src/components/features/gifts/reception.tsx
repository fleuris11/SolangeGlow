"use client";

import {
  CalendarCheck,
  Camera,
  Check,
  Copy,
  EnvelopeSimple,
  Gift,
  HourglassMedium,
  MapPin,
  Package,
  Sparkle,
  X,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { getSlots } from "@/lib/api/booking";
import { ApiError, hasSession } from "@/lib/api/client";
import {
  addGiftPhoto,
  answerProof,
  bookGift,
  claimGift,
  giftAsCard,
  openGift,
  receiveGift,
  type GiftReception as Reception,
  type GiftUse,
} from "@/lib/api/gifts";
import { dayName, timeAt } from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc, videoSrc, voiceSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";
import { usePreferences } from "@/lib/preferences/preferences-provider";

const key = (token: string) => ["gift", token];

function useRun() {
  const toast = useToast();
  const t = useTranslations("gifts.reception");
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
  return { busy, run };
}

/** The message of the giver: words, voice or video. */
function GiftMessage({ gift }: { gift: Reception }) {
  const t = useTranslations("gifts.reception");
  const { dataSaver } = usePreferences();
  const media = gift.message_media;
  return (
    <section
      className="flex flex-col gap-3"
      aria-label={t("messageFrom", { name: gift.from_name })}
    >
      {gift.message && (
        <blockquote className="bg-carte border-trait rounded-card text-lead border p-4 italic">
          « {gift.message} »
        </blockquote>
      )}
      {media?.kind === "audio" && voiceSrc(media) && (
        <audio controls src={voiceSrc(media)} className="w-full">
          <track kind="captions" />
        </audio>
      )}
      {media?.kind === "video" && videoSrc(media, dataSaver) && (
        <video
          controls
          playsInline
          preload="none"
          poster={mediaSrc(media, "medium")}
          src={videoSrc(media, dataSaver)}
          className="rounded-card aspect-video w-full bg-black"
        />
      )}
    </section>
  );
}

/** The offered service: choose a time, it is already paid. */
function BookPanel({ gift, token }: { gift: Reception; token: string }) {
  const t = useTranslations("gifts.reception");
  const locale = useLocale();
  const client = useQueryClient();
  const { busy, run } = useRun();
  const [day, setDay] = useState<string | null>(null);
  const [start, setStart] = useState<string | null>(null);
  const [name, setName] = useState(gift.recipient_name);
  const [phone, setPhone] = useState(gift.recipient_phone ?? "");
  const [done, setDone] = useState<string | null>(null);
  const slug = gift.pro?.slug ?? "";
  const zone = gift.time_zone ?? "Africa/Porto-Novo";
  const slots = useQuery({
    queryKey: ["gift-slots", slug, gift.service_id],
    queryFn: () => getSlots(slug, { service: gift.service_id ?? "", days: 14 }),
    enabled: Boolean(slug && gift.service_id),
  });
  const days = (slots.data?.days ?? []).filter((d) => d.slots.length > 0);
  const chosenDay = day ?? days[0]?.day ?? null;
  const times = days.find((d) => d.day === chosenDay)?.slots ?? [];
  const signedIn = hasSession();

  if (done) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <Bloom label={t("booked")} />
        <p className="text-title font-bold">{t("booked")}</p>
        <Link href={done} className={buttonClasses({ size: "lg" })}>
          <CalendarCheck aria-hidden size={24} />
          {t("seeAppointment")}
        </Link>
      </div>
    );
  }

  const book = () =>
    run(async () => {
      if (!start) return;
      const result = await bookGift(token, {
        start,
        guest_name: signedIn ? "" : name.trim(),
        guest_phone: signedIn ? "" : phone.trim(),
        note: "",
      });
      setDone(result.manage_url ?? `/appointments/${result.appointment.id}`);
      await client.invalidateQueries({ queryKey: key(token) });
    });

  return (
    <section aria-labelledby="book-title" className="flex flex-col gap-4">
      <h2 id="book-title" className="text-title font-bold">
        {t("chooseTime")}
      </h2>
      {slots.isPending && <Skeleton className="rounded-card h-32" />}
      {!slots.isPending && days.length === 0 && (
        <p className="bg-poudre rounded-2xl p-4">{t("noTime")}</p>
      )}
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
        {days.map((d) => (
          <button
            key={d.day}
            type="button"
            aria-pressed={d.day === chosenDay}
            onClick={() => {
              setDay(d.day);
              setStart(null);
            }}
            className={cn(
              "min-h-12 shrink-0 rounded-full border-2 px-4 font-bold",
              d.day === chosenDay ? "border-hibiscus bg-poudre" : "border-trait",
            )}
          >
            {dayName(d.day, locale, true)}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2">
        {times.map((slot) => (
          <button
            key={slot.start}
            type="button"
            aria-pressed={slot.start === start}
            onClick={() => setStart(slot.start)}
            className={cn(
              "min-h-12 rounded-2xl border-2 font-bold",
              slot.start === start ? "border-hibiscus bg-hibiscus text-lait" : "border-trait",
            )}
          >
            {timeAt(slot.start, zone, locale)}
          </button>
        ))}
      </div>
      {!signedIn && !gift.is_giver && (
        <div className="flex flex-col gap-3">
          <Input label={t("yourName")} value={name} onChange={(e) => setName(e.target.value)} />
          <Input
            label={t("yourPhone")}
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>
      )}
      <Button size="lg" fullWidth disabled={!start || busy} onClick={() => void book()}>
        <CalendarCheck aria-hidden size={24} />
        {start
          ? t("bookAt", {
              day: dayName(chosenDay ?? "", locale),
              time: timeAt(start, zone, locale),
            })
          : t("pickTime")}
      </Button>
      <p className="text-small text-prune-doux">{t("alreadyPaid")}</p>
    </section>
  );
}

/** The offered product: where she receives it, then the order leaves. */
function ReceivePanel({ gift, token }: { gift: Reception; token: string }) {
  const t = useTranslations("gifts.reception");
  const client = useQueryClient();
  const { busy, run } = useRun();
  const [address, setAddress] = useState("");
  const [landmarks, setLandmarks] = useState("");
  const [phone, setPhone] = useState(gift.recipient_phone ?? "");
  const points = gift.pickup_points ?? [];
  const [point, setPoint] = useState(points[0]?.id ?? "");
  const pickup = gift.kind === "product" && gift.thing?.delivery_mode === "pickup";

  const receive = () =>
    run(async () => {
      const fresh = await receiveGift(token, {
        address,
        landmarks,
        phone,
        ...(gift.kind === "selection" ? { pickup_point_id: point } : {}),
      });
      client.setQueryData(key(token), fresh);
    });

  return (
    <section aria-labelledby="receive-title" className="flex flex-col gap-4">
      <h2 id="receive-title" className="text-title font-bold">
        {gift.kind === "selection"
          ? t("wherePickup")
          : pickup
            ? t("pickupAtShop")
            : t("whereDeliver")}
      </h2>
      {gift.kind === "selection" ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="sr-only">{t("wherePickup")}</legend>
          {points.map((item) => (
            <label
              key={item.id}
              className={cn(
                "flex min-h-14 cursor-pointer items-start gap-3 rounded-2xl border-2 px-4 py-2",
                point === item.id ? "border-hibiscus bg-poudre" : "border-trait",
              )}
            >
              <input
                type="radio"
                name="point"
                className="sr-only"
                checked={point === item.id}
                onChange={() => setPoint(item.id)}
              />
              <MapPin aria-hidden size={24} className="text-hibiscus mt-1 shrink-0" />
              <span className="flex flex-col">
                <span className="font-bold">{item.name}</span>
                <span className="text-small text-prune-doux">
                  {[item.address, item.city].filter(Boolean).join(", ")}
                </span>
              </span>
            </label>
          ))}
        </fieldset>
      ) : (
        !pickup && (
          <div className="flex flex-col gap-3">
            {gift.thing?.zone && (
              <p className="text-small">{t("zone", { zone: gift.thing.zone })}</p>
            )}
            <Input
              label={t("address")}
              required
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
            <Input
              label={t("landmarks")}
              value={landmarks}
              onChange={(e) => setLandmarks(e.target.value)}
            />
            <Input
              label={t("deliveryPhone")}
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
        )
      )}
      <Button
        size="lg"
        fullWidth
        disabled={busy || (gift.kind === "selection" ? !point : !pickup && !address.trim())}
        onClick={() => void receive()}
      >
        <Package aria-hidden size={24} />
        {t("receive")}
      </Button>
    </section>
  );
}

/** A Glow gift card: its code, what is left, where it works. */
function CardPanel({ gift, token }: { gift: Reception; token: string }) {
  const t = useTranslations("gifts.reception");
  const locale = useLocale();
  const toast = useToast();
  const client = useQueryClient();
  const { busy, run } = useRun();
  const balance = gift.balance;
  const copy = async () => {
    await navigator.clipboard?.writeText(gift.code ?? "");
    toast(t("codeCopied"), "success");
  };
  return (
    <section aria-labelledby="card-title" className="flex flex-col gap-4">
      <div className="bg-hibiscus text-lait rounded-card flex flex-col gap-3 p-5">
        <p id="card-title" className="flex items-center gap-2 font-bold">
          <Sparkle aria-hidden size={24} weight="fill" />
          {t("cardName")}
        </p>
        {balance && (
          <p className="font-display text-display font-black">
            {formatMoney(balance.amount_minor, balance.currency, locale)}
          </p>
        )}
        {gift.code && (
          <p
            className="text-title font-bold tracking-widest"
            aria-label={t("codeIs", { code: gift.code.split("").join(" ") })}
          >
            {gift.code}
          </p>
        )}
        {gift.expires_on && (
          <p className="text-small">
            {t("until", {
              date: new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                new Date(`${gift.expires_on}T12:00:00Z`),
              ),
            })}
          </p>
        )}
      </div>
      {gift.code && (
        <Button variant="secondary" onClick={() => void copy()}>
          <Copy aria-hidden size={24} />
          {t("copyCode")}
        </Button>
      )}
      <p>{t("cardWhere")}</p>
      {hasSession() && !gift.is_giver
        ? !gift.claimed && (
            <Button
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  client.setQueryData(key(token), await claimGift(token));
                  toast(t("claimed"), "success");
                })
              }
            >
              <Check aria-hidden size={24} />
              {t("claim")}
            </Button>
          )
        : !gift.is_giver && (
            <Link href="/auth" className={buttonClasses({ size: "lg", fullWidth: true })}>
              {t("signInToUse")}
            </Link>
          )}
    </section>
  );
}

function UseLine({ use, zone }: { use: GiftUse; zone: string }) {
  const t = useTranslations("gifts.reception");
  const tStatus = useTranslations("gifts.useStatus");
  const locale = useLocale();
  return (
    <li className="border-trait rounded-card flex flex-col gap-2 border p-4">
      <p className="font-bold">{use.label}</p>
      {use.starts_at && (
        <p>
          {t("on", {
            day: dayName(use.starts_at.slice(0, 10), locale),
            time: timeAt(use.starts_at, zone, locale),
          })}
        </p>
      )}
      {use.status && tStatus.has(use.status as "pending") && (
        <p className="bg-poudre text-small self-start rounded-full px-3 py-1 font-bold">
          {tStatus(use.status as "pending")}
        </p>
      )}
      {use.pickup_point && (
        <p className="text-small">{t("pickupAt", { place: use.pickup_point })}</p>
      )}
      {use.receipt_code && (
        <div className="bg-poudre flex flex-col gap-1 rounded-2xl p-3">
          <p className="text-small font-bold">{t("receiptCode")}</p>
          <p className="text-headline font-bold tracking-widest">{use.receipt_code}</p>
          <p className="text-small text-prune-doux">{t("receiptHelp")}</p>
        </div>
      )}
      {use.link && (
        <Link href={use.link} className="text-hibiscus font-bold underline">
          {t("seeDetails")}
        </Link>
      )}
    </li>
  );
}

/** Proof of joy: photos of the result, sent to the giver only with her yes. */
function ProofPanel({ gift, token }: { gift: Reception; token: string }) {
  const t = useTranslations("gifts.reception");
  const client = useQueryClient();
  const { busy, run } = useRun();
  const photos = gift.photos ?? [];
  if (gift.proof_status === "sent") {
    return (
      <p className="bg-poudre flex items-center gap-2 rounded-2xl p-4 font-bold">
        <Check aria-hidden size={24} className="text-feuille" />
        {t("proofSent", { name: gift.from_name })}
      </p>
    );
  }
  const answer = (mediaId: string | null, send: boolean) =>
    run(async () => {
      client.setQueryData(key(token), await answerProof(token, { media_id: mediaId, send }));
    });
  return (
    <section aria-labelledby="proof-title" className="flex flex-col gap-3">
      <h2 id="proof-title" className="text-title font-bold">
        {t("proofTitle", { name: gift.from_name })}
      </h2>
      <p className="text-small text-prune-doux">{t("proofHelp")}</p>
      {photos.map((photo) => (
        <figure key={photo.id} className="flex flex-col gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={mediaSrc(photo.media, "medium", "large")}
            alt={t("proofPhoto")}
            className="rounded-card aspect-square w-full object-cover"
          />
          <div className="grid grid-cols-2 gap-2">
            <Button disabled={busy} onClick={() => void answer(photo.id, true)}>
              <Check aria-hidden size={20} />
              {t("proofYes")}
            </Button>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => void answer(photo.id, false)}
            >
              <X aria-hidden size={20} />
              {t("proofNo")}
            </Button>
          </div>
        </figure>
      ))}
      <label
        className={cn(
          buttonClasses({ variant: "secondary" }),
          "cursor-pointer",
          busy && "opacity-60",
        )}
      >
        <Camera aria-hidden size={24} />
        {t("addPhoto")}
        <input
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) {
              void run(async () => {
                client.setQueryData(key(token), await addGiftPhoto(token, file));
              });
            }
          }}
        />
      </label>
      {gift.proof_status === "declined" && <p className="text-small">{t("proofDeclined")}</p>}
    </section>
  );
}

function Envelope({ gift, onOpen }: { gift: Reception; onOpen: () => void }) {
  const t = useTranslations("gifts.reception");
  const tOccasions = useTranslations("gifts.occasions");
  return (
    <div className="flex flex-col items-center gap-6 py-6 text-center">
      <div className="bg-hibiscus text-lait rounded-card relative flex aspect-[4/3] w-full max-w-sm flex-col items-center justify-center gap-3 overflow-hidden">
        <span
          aria-hidden
          className="bg-or absolute -top-1/2 left-1/2 aspect-square w-3/4 -translate-x-1/2 rotate-45 rounded-3xl opacity-90"
        />
        <Gift aria-hidden size={72} weight="duotone" className="relative" />
      </div>
      <h1 className="font-display text-display font-black">
        {t("forYou", { name: gift.recipient_name })}
      </h1>
      <p className="text-lead">
        {gift.occasion !== "none"
          ? t("fromWithOccasion", { name: gift.from_name, occasion: tOccasions(gift.occasion) })
          : t("from", { name: gift.from_name })}
      </p>
      <Button size="lg" fullWidth onClick={onOpen}>
        <EnvelopeSimple aria-hidden size={24} />
        {t("open")}
      </Button>
    </div>
  );
}

/** The page of the gift: closed until its day, then the envelope opens (éclosion). */
export function GiftReception({ token }: { token: string }) {
  const t = useTranslations("gifts.reception");
  const tOccasions = useTranslations("gifts.occasions");
  const locale = useLocale();
  const { busy, run } = useRun();
  const client = useQueryClient();
  const [opened, setOpened] = useState(false);
  const query = useQuery({ queryKey: key(token), queryFn: () => openGift(token), retry: false });

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const gift = query.data;
  if (!gift) {
    return (
      <p role="alert" className="text-lead font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }

  if (gift.locked) {
    const date = new Intl.DateTimeFormat(locale, { day: "numeric", month: "long" }).format(
      new Date(gift.opens_at),
    );
    return (
      <div className="flex flex-col items-center gap-4 py-10 text-center">
        <HourglassMedium aria-hidden size={72} weight="duotone" className="text-hibiscus" />
        <h1 className="font-display text-display font-black">{t("waitTitle")}</h1>
        <p className="text-lead">{t("waitText", { name: gift.from_name, date })}</p>
      </div>
    );
  }

  const used = (gift.uses ?? []).length > 0;
  if (!opened && !used && !gift.is_giver) {
    return <Envelope gift={gift} onOpen={() => setOpened(true)} />;
  }

  const thing = gift.thing;
  const value = gift.value;
  const zone = gift.time_zone ?? "Africa/Porto-Novo";
  const title = t("giftFrom", { name: gift.from_name });
  let panel: ReactNode = null;
  if (gift.expired) panel = <p className="bg-poudre rounded-2xl p-4 font-bold">{t("expired")}</p>;
  else if (gift.cancelled)
    panel = <p className="bg-poudre rounded-2xl p-4 font-bold">{t("cancelled")}</p>;
  else if (gift.kind === "card") panel = <CardPanel gift={gift} token={token} />;
  else if (gift.unused && thing && !thing.available) {
    panel = (
      <div className="bg-poudre flex flex-col gap-3 rounded-2xl p-4">
        <p className="font-bold">{t("unavailable")}</p>
        <Button
          disabled={busy}
          onClick={() =>
            void run(async () => {
              client.setQueryData(key(token), await giftAsCard(token));
            })
          }
        >
          <Sparkle aria-hidden size={24} />
          {t("asCard", {
            value: value ? formatMoney(value.amount_minor, value.currency, locale) : "",
          })}
        </Button>
      </div>
    );
  } else if (gift.unused && gift.kind === "service")
    panel = <BookPanel gift={gift} token={token} />;
  else if (gift.unused) panel = <ReceivePanel gift={gift} token={token} />;

  return (
    <div className="flex flex-col gap-6">
      {gift.is_giver && (
        <p className="bg-or text-sur-or rounded-2xl p-3 font-bold">
          {t("preview", { name: gift.recipient_name })}
        </p>
      )}
      <header className="flex flex-col items-center gap-3 text-center">
        {opened && <Bloom label={t("opened")} />}
        <h1 className="font-display text-display font-black">{title}</h1>
        {gift.occasion !== "none" && <p className="text-lead">{tOccasions(gift.occasion)}</p>}
        <SpeakButton text={[title, gift.message, gift.title].filter(Boolean).join(". ")} />
      </header>
      <GiftMessage gift={gift} />
      {gift.kind !== "card" && (
        <section className="border-trait bg-carte rounded-card flex items-center gap-4 border p-4">
          {mediaSrc(thing?.photo ?? gift.pro?.photo, "thumb") ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={mediaSrc(thing?.photo ?? gift.pro?.photo, "thumb")}
              alt=""
              className="petal size-20 shrink-0 object-cover"
            />
          ) : (
            <Gift aria-hidden size={48} weight="duotone" className="text-hibiscus shrink-0" />
          )}
          <div className="flex flex-col gap-1">
            <p className="text-lead font-bold">{thing?.name}</p>
            {gift.pro && <p className="text-prune-doux">{gift.pro.name}</p>}
            {thing?.variant && <p className="text-small">{thing.variant}</p>}
            {value && (
              <p className="text-small font-bold">
                {t("paidFor", { value: formatMoney(value.amount_minor, value.currency, locale) })}
              </p>
            )}
            {gift.expires_on && (
              <p className="text-small text-prune-doux">
                {t("until", {
                  date: new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                    new Date(`${gift.expires_on}T12:00:00Z`),
                  ),
                })}
              </p>
            )}
          </div>
        </section>
      )}
      {panel}
      {used && (
        <section aria-labelledby="uses-title" className="flex flex-col gap-3">
          <h2 id="uses-title" className="text-title font-bold">
            {t("usesTitle")}
          </h2>
          <ul className="flex flex-col gap-3">
            {(gift.uses ?? []).map((use) => (
              <UseLine key={use.id} use={use} zone={zone} />
            ))}
          </ul>
        </section>
      )}
      {used && !gift.is_giver && <ProofPanel gift={gift} token={token} />}
    </div>
  );
}
