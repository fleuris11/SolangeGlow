"use client";

import {
  CalendarBlank,
  Gift,
  LockKey,
  Microphone,
  Scissors,
  ShoppingBag,
  Sparkle,
  Trash,
  VideoCamera,
} from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { getBookingPage } from "@/lib/api/booking";
import { ApiError } from "@/lib/api/client";
import {
  getGiftIdeas,
  getGiftQuote,
  getProductOptions,
  offerGift,
  OCCASIONS,
  uploadGiftMessage,
  type GiftKind,
  type Occasion,
  type QuoteQuery,
} from "@/lib/api/gifts";
import { useMe } from "@/lib/auth/use-me";
import { zonedToIso } from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney, parseMoney } from "@/lib/money";

import { HoldToRecord } from "../messaging/hold-to-record";

/** Where the person receives the gift: the hour of the sending, in Benin. */
const RECIPIENT_ZONE = "Africa/Porto-Novo";
const SEND_MINUTES = 8 * 60;
const CARD_STEPS = [2_000, 3_000, 5_000, 10_000];

export type OfferStart = {
  kind?: GiftKind;
  pro?: string;
  service?: string;
  variant?: string;
  selection_product?: string;
  option?: string;
};

function Choice({
  selected,
  onSelect,
  name,
  children,
}: {
  selected: boolean;
  onSelect: () => void;
  name: string;
  children: ReactNode;
}) {
  return (
    <label
      className={cn(
        "flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 px-4 py-2",
        selected ? "border-hibiscus bg-poudre" : "border-trait",
      )}
    >
      <input type="radio" name={name} checked={selected} onChange={onSelect} className="sr-only" />
      {children}
    </label>
  );
}

/** Step 1 without a chosen thing: a service, a product, or a Glow gift card. */
function Hub({
  amount,
  setAmount,
  summary,
}: {
  amount: string;
  setAmount: (value: string) => void;
  summary: ReactNode;
}) {
  const t = useTranslations("gifts.offer");
  const locale = useLocale();
  const ideas = useQuery({ queryKey: ["gift-ideas"], queryFn: getGiftIdeas });
  // A few ideas only: the page stays short on a small phone.
  const products = [
    ...(ideas.data?.products ?? []).slice(0, 4),
    ...(ideas.data?.selection ?? []).slice(0, 2),
  ];
  return (
    <div className="flex flex-col gap-6">
      <section className="border-trait rounded-card flex flex-col gap-3 border p-4">
        <h2 className="text-lead flex items-center gap-2 font-bold">
          <Sparkle aria-hidden size={24} weight="duotone" className="text-hibiscus" />
          {t("cardTitle")}
        </h2>
        <p className="text-small text-prune-doux">{t("cardHelp")}</p>
        <div className="flex flex-wrap gap-2">
          {CARD_STEPS.map((cents) => (
            <Chip
              key={cents}
              selected={parseMoney(amount, "EUR") === cents}
              onClick={() => setAmount(String(cents / 100))}
            >
              {formatMoney(cents, "EUR", locale)}
            </Chip>
          ))}
        </div>
        <Input
          label={t("amount")}
          inputMode="decimal"
          value={amount}
          trailing={<span aria-hidden>€</span>}
          hint={
            ideas.data
              ? t("amountHint", {
                  min: formatMoney(ideas.data.card_min.amount_minor, "EUR", locale),
                  max: formatMoney(ideas.data.card_max.amount_minor, "EUR", locale),
                })
              : undefined
          }
          onChange={(event) => setAmount(event.target.value)}
        />
        {summary}
      </section>
      <section className="border-trait rounded-card flex flex-col gap-3 border p-4">
        <h2 className="text-lead flex items-center gap-2 font-bold">
          <Scissors aria-hidden size={24} weight="duotone" className="text-hibiscus" />
          {t("serviceTitle")}
        </h2>
        <p className="text-small text-prune-doux">{t("serviceHelp")}</p>
        <Link href="/explore" className={buttonClasses({ variant: "secondary" })}>
          {t("findPro")}
        </Link>
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-lead flex items-center gap-2 font-bold">
          <ShoppingBag aria-hidden size={24} weight="duotone" className="text-hibiscus" />
          {t("productTitle")}
        </h2>
        <p className="text-small text-prune-doux">{t("productHelp")}</p>
        {ideas.isPending && <Skeleton className="rounded-card h-40" />}
        <ul className="grid grid-cols-2 gap-3">
          {products.map((idea) => (
            <li key={idea.id}>
              <Link
                href={
                  idea.kind === "selection"
                    ? `/selection/${idea.slug}`
                    : `/${idea.shop}/shop/${idea.slug}`
                }
                className="border-trait bg-carte rounded-card flex h-full flex-col gap-2 border p-2"
              >
                {mediaSrc(idea.photo, "thumb", "medium") ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={mediaSrc(idea.photo, "thumb", "medium")}
                    alt=""
                    className="aspect-square w-full rounded-2xl object-cover"
                    loading="lazy"
                  />
                ) : (
                  <span className="bg-poudre aspect-square w-full rounded-2xl" aria-hidden />
                )}
                <span className="line-clamp-2 font-bold">{idea.title}</span>
                <span className="text-small text-prune-doux">{idea.shop_name}</span>
                <span className="font-bold">
                  {formatMoney(idea.price.amount_minor, idea.price.currency, locale)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

/** Step 1 with a pro: which of her services. */
function ServicePick({
  pro,
  service,
  setService,
}: {
  pro: string;
  service: string;
  setService: (id: string) => void;
}) {
  const t = useTranslations("gifts.offer");
  const locale = useLocale();
  const page = useQuery({ queryKey: ["booking-page", pro], queryFn: () => getBookingPage(pro) });
  if (page.isPending) return <Skeleton className="rounded-card h-60" />;
  const services = (page.data?.services ?? []).filter(
    (s) => s.price_kind === "fixed" && s.price_minor && s.currency === "XOF",
  );
  if (!page.data || services.length === 0) {
    return <p className="bg-poudre rounded-2xl p-4 font-bold">{t("noService")}</p>;
  }
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="text-lead mb-2 font-bold">
        {t("whichService", { name: page.data.pro.name })}
      </legend>
      {services.map((item) => (
        <Choice
          key={item.id}
          name="service"
          selected={service === item.id}
          onSelect={() => setService(item.id)}
        >
          <span className="flex-1 font-bold">{item.name}</span>
          <span>{formatMoney(item.price_minor ?? 0, item.currency, locale)}</span>
        </Choice>
      ))}
    </fieldset>
  );
}

/** Step 1 with a product: how it reaches her (pick-up at the shop or a delivery zone). */
function DeliveryPick({
  variant,
  value,
  setValue,
}: {
  variant: string;
  value: { mode: string; zone: string };
  setValue: (value: { mode: string; zone: string }) => void;
}) {
  const t = useTranslations("gifts.offer");
  const locale = useLocale();
  const options = useQuery({
    queryKey: ["gift-options", variant],
    queryFn: () => getProductOptions(variant),
  });
  if (options.isPending) return <Skeleton className="rounded-card h-40" />;
  const data = options.data;
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="text-lead mb-2 font-bold">{t("howDelivered")}</legend>
      {data?.pickup && (
        <Choice
          name="delivery"
          selected={value.mode === "pickup"}
          onSelect={() => setValue({ mode: "pickup", zone: "" })}
        >
          <span className="flex-1 font-bold">{t("pickup")}</span>
          <span>{t("free")}</span>
        </Choice>
      )}
      {data?.zones.map((zone) => (
        <Choice
          key={zone.id}
          name="delivery"
          selected={value.zone === zone.id}
          onSelect={() => setValue({ mode: zone.mode, zone: zone.id })}
        >
          <span className="flex-1 font-bold">{t("deliveredIn", { zone: zone.name })}</span>
          <span>{formatMoney(zone.fee.amount_minor, zone.fee.currency, locale)}</span>
        </Choice>
      ))}
      <p className="text-small text-prune-doux">{t("addressLater")}</p>
    </fieldset>
  );
}

/** The voice or video message: recorded here, or a video chosen from the phone. */
function MessageMedia({
  value,
  onChange,
}: {
  value: { id: string; kind: "audio" | "video" } | null;
  onChange: (value: { id: string; kind: "audio" | "video" } | null) => void;
}) {
  const t = useTranslations("gifts.offer");
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  const send = async (file: Blob, kind: "audio" | "video") => {
    setBusy(true);
    try {
      const media = await uploadGiftMessage(file);
      onChange({ id: media.id, kind });
      toast(t(kind === "audio" ? "voiceAdded" : "videoAdded"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  if (value) {
    return (
      <div className="bg-poudre flex items-center gap-3 rounded-2xl p-3">
        {value.kind === "audio" ? (
          <Microphone aria-hidden size={24} weight="duotone" />
        ) : (
          <VideoCamera aria-hidden size={24} weight="duotone" />
        )}
        <span className="flex-1 font-bold">
          {t(value.kind === "audio" ? "voiceReady" : "videoReady")}
        </span>
        <Button variant="quiet" onClick={() => onChange(null)}>
          <Trash aria-hidden size={20} />
          {t("remove")}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <HoldToRecord onRecorded={(file) => void send(file, "audio")} />
        <span className="text-small text-prune-doux">{t("voiceHelp")}</span>
      </div>
      <label
        className={cn(
          buttonClasses({ variant: "secondary" }),
          "cursor-pointer",
          busy && "pointer-events-none opacity-60",
        )}
      >
        <VideoCamera aria-hidden size={24} />
        {t("addVideo")}
        <input
          type="file"
          accept="video/*"
          capture="user"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void send(file, "video");
            event.target.value = "";
          }}
        />
      </label>
    </div>
  );
}

/** « Offer » in 4 steps: what, for whom, the message and its day, the payment in euros. */
export function OfferFlow({ start }: { start: OfferStart }) {
  const t = useTranslations("gifts.offer");
  const tOccasions = useTranslations("gifts.occasions");
  const locale = useLocale();
  const toast = useToast();
  const me = useMe().data;
  const initialKind: GiftKind | null =
    start.service || start.pro
      ? "service"
      : start.variant
        ? "product"
        : start.selection_product
          ? "selection"
          : null;
  const [step, setStep] = useState(1);
  const [service, setService] = useState(start.service ?? "");
  const [amount, setAmount] = useState(start.kind === "card" ? "30" : "");
  const [delivery, setDelivery] = useState({ mode: "", zone: "" });
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [occasion, setOccasion] = useState<Occasion>("none");
  const [fromName, setFromName] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [media, setMedia] = useState<{ id: string; kind: "audio" | "video" } | null>(null);
  const [later, setLater] = useState(false);
  const [day, setDay] = useState("");
  const [busy, setBusy] = useState(false);

  const kind: GiftKind = initialKind ?? "card";
  const cents = parseMoney(amount, "EUR");
  const query: QuoteQuery | null =
    kind === "service"
      ? service
        ? { kind, service }
        : null
      : kind === "product"
        ? delivery.mode
          ? {
              kind,
              variant: start.variant,
              delivery_mode: delivery.mode,
              ...(delivery.zone ? { zone: delivery.zone } : {}),
            }
          : null
        : kind === "selection"
          ? { kind, selection_product: start.selection_product, option: start.option ?? "" }
          : cents
            ? { kind, amount_minor: cents }
            : null;
  const quote = useQuery({
    queryKey: ["gift-quote", query],
    queryFn: () => getGiftQuote(query!),
    enabled: query !== null,
    retry: false,
  });
  const giver = fromName ?? me?.first_name ?? "";
  const money = (value: { amount_minor: number; currency: string }) =>
    formatMoney(value.amount_minor, value.currency, locale);

  const pay = async () => {
    if (!query) return;
    setBusy(true);
    try {
      const result = await offerGift({
        ...query,
        delivery_mode: query.delivery_mode ?? "",
        option: query.option ?? "",
        recipient_name: name.trim(),
        recipient_phone: phone.trim(),
        recipient_email: email.trim(),
        language: locale === "en" || locale === "sk" ? locale : "fr",
        occasion,
        message: message.trim(),
        message_media_id: media?.id ?? null,
        send_at: later && day ? zonedToIso(day, SEND_MINUTES, RECIPIENT_ZONE) : null,
        from_name: giver.trim(),
      });
      window.location.assign(result.checkout_url);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      setBusy(false);
    }
  };

  const summary = quote.data ? (
    <section aria-live="polite" className="bg-poudre rounded-card flex items-center gap-3 p-4">
      {mediaSrc(quote.data.photo, "thumb") ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={mediaSrc(quote.data.photo, "thumb")}
          alt=""
          className="petal size-16 shrink-0 object-cover"
        />
      ) : (
        <Gift aria-hidden size={40} weight="duotone" className="text-hibiscus shrink-0" />
      )}
      <span className="flex flex-col">
        <span className="font-bold">{quote.data.title}</span>
        <span>
          {t("worth", { value: money(quote.data.value), price: money(quote.data.price) })}
        </span>
      </span>
    </section>
  ) : null;

  const titles = [t("step1"), t("step2"), t("step3"), t("step4")];
  const title = titles[step - 1] ?? "";
  const quoteError = quote.error instanceof ApiError ? quote.error.message : null;
  const canGoOn =
    step === 1
      ? quote.isSuccess
      : step === 2
        ? name.trim().length > 0 && phone.trim().length >= 8
        : step === 3
          ? !later || day.length > 0
          : true;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="flex flex-col gap-6">
      <Stepper current={step} total={4} onBack={() => setStep(step - 1)} />
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{title}</h1>
        <SpeakButton text={title} />
      </div>

      {step === 1 && (
        <div className="flex flex-col gap-6">
          {kind === "card" && <Hub amount={amount} setAmount={setAmount} summary={summary} />}
          {kind === "service" && start.pro && (
            <ServicePick pro={start.pro} service={service} setService={setService} />
          )}
          {kind === "product" && start.variant && (
            <DeliveryPick variant={start.variant} value={delivery} setValue={setDelivery} />
          )}
          {kind !== "card" && summary}
          {quoteError && query && (
            <p role="alert" className="text-alerte font-bold">
              {quoteError}
            </p>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-4">
          <Input
            label={t("recipientName")}
            required
            maxLength={80}
            value={name}
            autoComplete="off"
            onChange={(event) => setName(event.target.value)}
          />
          <Input
            label={t("recipientPhone")}
            hint={t("recipientPhoneHint")}
            required
            type="tel"
            inputMode="tel"
            value={phone}
            placeholder="+229 01 97 00 00 00"
            onChange={(event) => setPhone(event.target.value)}
          />
          <Input
            label={t("recipientEmail")}
            hint={t("recipientEmailHint")}
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("occasion")}</legend>
            <div className="flex flex-wrap gap-2">
              {OCCASIONS.map((value) => (
                <Chip key={value} selected={occasion === value} onClick={() => setOccasion(value)}>
                  {tOccasions(value)}
                </Chip>
              ))}
            </div>
          </fieldset>
          <Input
            label={t("fromName")}
            maxLength={80}
            value={giver}
            onChange={(event) => setFromName(event.target.value)}
          />
        </div>
      )}

      {step === 3 && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label htmlFor="gift-message" className="font-bold">
              {t("message")}
            </label>
            <textarea
              id="gift-message"
              maxLength={500}
              rows={4}
              value={message}
              placeholder={t("messagePlaceholder")}
              onChange={(event) => setMessage(event.target.value)}
              className="rounded-field bg-poudre focus:border-hibiscus border-2 border-transparent p-4 outline-none"
            />
          </div>
          <MessageMedia value={media} onChange={setMedia} />
          <fieldset className="flex flex-col gap-3">
            <legend className="mb-2 font-bold">{t("when")}</legend>
            <Choice name="when" selected={!later} onSelect={() => setLater(false)}>
              <Gift aria-hidden size={24} weight="duotone" className="text-hibiscus" />
              <span className="font-bold">{t("now")}</span>
            </Choice>
            <Choice name="when" selected={later} onSelect={() => setLater(true)}>
              <CalendarBlank aria-hidden size={24} weight="duotone" className="text-hibiscus" />
              <span className="font-bold">{t("onDay")}</span>
            </Choice>
            {later && (
              <Input
                label={t("day")}
                type="date"
                min={today}
                value={day}
                hint={t("dayHint")}
                onChange={(event) => setDay(event.target.value)}
              />
            )}
          </fieldset>
        </div>
      )}

      {step === 4 && quote.data && (
        <div className="flex flex-col gap-5">
          <dl className="border-trait rounded-card flex flex-col gap-2 border p-4">
            {[
              [t("summaryWhat"), quote.data.title],
              [t("summaryFor"), name],
              [t("summaryWorth"), money(quote.data.value)],
              [t("summaryPrice"), money(quote.data.price)],
              [t("summaryFee"), money(quote.data.fee)],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4">
                <dt>{label}</dt>
                <dd className="text-right font-bold">{value}</dd>
              </div>
            ))}
            <div className="text-title flex justify-between gap-4 font-bold">
              <dt>{t("summaryTotal")}</dt>
              <dd className="text-right">{money(quote.data.total)}</dd>
            </div>
          </dl>
          <ul className="flex flex-col gap-3">
            <li className="bg-poudre flex items-start gap-3 rounded-2xl p-4">
              <LockKey aria-hidden size={28} weight="duotone" className="text-hibiscus shrink-0" />
              <span>{t("safe", { days: quote.data.cancel_days })}</span>
            </li>
            <li className="bg-poudre flex items-start gap-3 rounded-2xl p-4">
              <CalendarBlank
                aria-hidden
                size={28}
                weight="duotone"
                className="text-hibiscus shrink-0"
              />
              <span>{t("valid", { days: quote.data.validity_days })}</span>
            </li>
          </ul>
          <p className="text-small text-prune-doux">
            {t("rate", {
              rate: Number(quote.data.rate).toLocaleString(locale, { maximumFractionDigits: 3 }),
            })}
          </p>
        </div>
      )}

      {step < 4 ? (
        <Button size="lg" fullWidth disabled={!canGoOn} onClick={() => setStep(step + 1)}>
          {t("next")}
        </Button>
      ) : (
        quote.data && (
          <Button size="lg" fullWidth disabled={busy} onClick={() => void pay()}>
            <LockKey aria-hidden size={24} weight="bold" />
            {t("pay", { amount: money(quote.data.total) })}
          </Button>
        )
      )}
    </div>
  );
}
