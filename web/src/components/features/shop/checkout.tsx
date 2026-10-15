"use client";

import { LockKey, Moped, ShieldCheck, Storefront, Truck } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  getCart,
  getQuote,
  placeOrders,
  type CartShop,
  type DeliveryMode,
  type Quote,
  type ShopChoice,
} from "@/lib/api/shop";
import { useMe } from "@/lib/auth/use-me";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

import { CART_KEY } from "./cart";

type Choice = { mode: DeliveryMode; zoneId: string | null; promo: string; note: string };

const MODE_ICONS: Record<DeliveryMode, ReactNode> = {
  pickup: <Storefront aria-hidden size={24} weight="duotone" />,
  seller: <Moped aria-hidden size={24} weight="duotone" />,
  partner: <Truck aria-hidden size={24} weight="duotone" />,
};

function modesOf(shop: CartShop): DeliveryMode[] {
  const d = shop.delivery;
  return [
    ...(d.pickup ? (["pickup"] as const) : []),
    ...(d.seller_delivery && d.zones.some((z) => z.mode === "seller") ? (["seller"] as const) : []),
    ...(d.partner_delivery && d.zones.some((z) => z.mode === "partner")
      ? (["partner"] as const)
      : []),
  ];
}

function Option({
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

/** Step 1: how each shop hands over, a promo code, a note. */
function HandOver({
  shops,
  choices,
  setChoice,
}: {
  shops: CartShop[];
  choices: Record<string, Choice>;
  setChoice: (proId: string, choice: Partial<Choice>) => void;
}) {
  const t = useTranslations("shop.checkout");
  const tModes = useTranslations("shop.modes");
  const locale = useLocale();
  return (
    <div className="flex flex-col gap-6">
      {shops.map((shop) => {
        const choice = choices[shop.pro_id];
        if (!choice) return null;
        const zones = shop.delivery.zones.filter((z) => z.mode === choice.mode);
        return (
          <fieldset
            key={shop.pro_id}
            className="border-trait rounded-card flex flex-col gap-3 border p-4"
          >
            <legend className="text-lead px-1 font-bold">{shop.shop.name}</legend>
            <p className="text-small text-prune-doux">
              {t("articles", { count: shop.lines.length })}
              {shop.prep_days > 0 && ` ${t("prep", { count: shop.prep_days })}`}
            </p>
            {modesOf(shop).map((mode) => (
              <Option
                key={mode}
                name={`mode-${shop.pro_id}`}
                selected={choice.mode === mode}
                onSelect={() => {
                  const first = shop.delivery.zones.find((z) => z.mode === mode);
                  setChoice(shop.pro_id, {
                    mode,
                    zoneId: mode === "pickup" ? null : (first?.id ?? null),
                  });
                }}
              >
                <span className="text-hibiscus">{MODE_ICONS[mode]}</span>
                <span className="flex flex-col">
                  <span className="font-bold">
                    {mode === "partner" && shop.delivery.partner_name
                      ? tModes("partnerNamed", { name: shop.delivery.partner_name })
                      : tModes(mode)}
                  </span>
                  {mode === "pickup" && shop.delivery.pickup_note && (
                    <span className="text-small text-prune-doux">{shop.delivery.pickup_note}</span>
                  )}
                </span>
              </Option>
            ))}
            {choice.mode !== "pickup" && zones.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="font-bold">{t("zone")}</p>
                {zones.map((zone) => (
                  <Option
                    key={zone.id}
                    name={`zone-${shop.pro_id}`}
                    selected={choice.zoneId === zone.id}
                    onSelect={() => setChoice(shop.pro_id, { zoneId: zone.id })}
                  >
                    <span className="flex-1 font-bold">{zone.name}</span>
                    <span>{formatMoney(zone.fee_minor, shop.currency, locale)}</span>
                  </Option>
                ))}
              </div>
            )}
            <Input
              label={t("promo")}
              value={choice.promo}
              autoCapitalize="characters"
              maxLength={20}
              onChange={(event) => setChoice(shop.pro_id, { promo: event.target.value })}
            />
            <Input
              label={t("note")}
              value={choice.note}
              maxLength={300}
              onChange={(event) => setChoice(shop.pro_id, { note: event.target.value })}
            />
          </fieldset>
        );
      })}
    </div>
  );
}

/** Step 2: what each order costs, read aloud on demand. */
function Summary({ quote }: { quote: Quote }) {
  const t = useTranslations("shop.checkout");
  const tModes = useTranslations("shop.modes");
  const locale = useLocale();
  const money = (value: number) => formatMoney(value, quote.currency, locale);
  const spoken = [
    ...quote.orders.map((order) =>
      t("spokenOrder", { shop: order.shop, total: money(order.total_minor) }),
    ),
    t("spokenTotal", { total: money(quote.total_minor) }),
  ].join(". ");
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <h2 className="text-title flex-1 font-bold">{t("summaryTitle")}</h2>
        <SpeakButton text={spoken} />
      </div>
      {quote.orders.map((order) => (
        <section
          key={order.pro_id}
          className="border-trait rounded-card flex flex-col gap-2 border p-4"
        >
          <h3 className="text-lead font-bold">{order.shop}</h3>
          <p className="text-small text-prune-doux">
            {tModes(order.delivery_mode)}
            {order.zone && ` (${order.zone})`}
          </p>
          <dl className="flex flex-col gap-1">
            {[
              [t("items"), money(order.subtotal_minor)],
              ...(order.discount_minor
                ? [[t("discount", { code: order.promo_code }), `− ${money(order.discount_minor)}`]]
                : []),
              [t("delivery"), order.delivery_minor ? money(order.delivery_minor) : t("free")],
              [t("protection"), money(order.buyer_fee_minor)],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4">
                <dt>{label}</dt>
                <dd className="text-right">{value}</dd>
              </div>
            ))}
            <div className="flex justify-between gap-4 font-bold">
              <dt>{t("orderTotal")}</dt>
              <dd className="text-right">{money(order.total_minor)}</dd>
            </div>
          </dl>
        </section>
      ))}
      <p className="text-small text-prune-doux">{t("protectionHelp")}</p>
      <p className="text-title flex justify-between font-bold">
        <span>{t("total")}</span>
        <span>{money(quote.total_minor)}</span>
      </p>
    </div>
  );
}

/** The checkout in 3 steps: hand-over, summary, payment (one payment for every shop). */
export function CheckoutFlow() {
  const t = useTranslations("shop.checkout");
  const locale = useLocale();
  const toast = useToast();
  const me = useMe().data;
  const cart = useQuery({ queryKey: CART_KEY, queryFn: getCart });
  const [step, setStep] = useState(1);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [address, setAddress] = useState("");
  const [landmarks, setLandmarks] = useState("");
  const [phone, setPhone] = useState<string | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [busy, setBusy] = useState(false);

  if (cart.isPending) return <Skeleton className="rounded-card h-80" />;
  const allShops = cart.data?.shops ?? [];
  const ready = allShops.filter(
    (shop) =>
      shop.delivery.is_open &&
      modesOf(shop).length > 0 &&
      shop.lines.every((l) => l.available && l.stock_left >= l.quantity),
  );
  const currency = ready[0]?.currency;
  const shops = ready.filter((shop) => shop.currency === currency);
  if (shops.length === 0) {
    return (
      <div className="flex flex-col items-start gap-4">
        <p className="text-lead font-bold">{t("nothing")}</p>
        <Link href="/cart" className={buttonClasses({ variant: "secondary" })}>
          {t("backToCart")}
        </Link>
      </div>
    );
  }
  const current: Record<string, Choice> = Object.fromEntries(
    shops.map((shop) => [
      shop.pro_id,
      choices[shop.pro_id] ?? {
        mode: modesOf(shop)[0] ?? "pickup",
        zoneId: null,
        promo: "",
        note: "",
      },
    ]),
  );
  const setChoice = (proId: string, change: Partial<Choice>) => {
    const base = current[proId];
    if (base) setChoices({ ...current, [proId]: { ...base, ...change } });
  };
  const delivering = Object.values(current).some((c) => c.mode !== "pickup");
  const phoneValue = phone ?? me?.phone ?? "";
  const body: ShopChoice[] = shops.map((shop) => {
    const choice = current[shop.pro_id]!; // every shop has its choice (above)
    return {
      pro_id: shop.pro_id,
      delivery_mode: choice.mode,
      zone_id: choice.mode === "pickup" ? null : choice.zoneId,
      promo_code: choice.promo.trim(),
      note: choice.note.trim(),
    };
  });

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

  const toSummary = () =>
    run(async () => {
      setQuote(await getQuote(body));
      setStep(2);
    });

  const pay = () =>
    run(async () => {
      const result = await placeOrders({
        shops: body,
        address: delivering ? address : "",
        landmarks: delivering ? landmarks : "",
        phone: delivering ? phoneValue : "",
      });
      window.location.assign(result.checkout_url);
    });

  const titles = [t("step1"), t("step2"), t("step3")];
  return (
    <div className="flex flex-col gap-6">
      <Stepper current={step} total={3} onBack={() => setStep(step - 1)} />
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{titles[step - 1] ?? ""}</h1>
        <SpeakButton text={titles[step - 1] ?? ""} />
      </div>

      {step === 1 && (
        <form
          className="flex flex-col gap-6"
          onSubmit={(event) => {
            event.preventDefault();
            void toSummary();
          }}
        >
          <HandOver shops={shops} choices={current} setChoice={setChoice} />
          {delivering && (
            <fieldset className="flex flex-col gap-3">
              <legend className="text-lead mb-2 font-bold">{t("whereTitle")}</legend>
              <p className="text-small text-prune-doux">{t("whereHelp")}</p>
              <Input
                label={t("address")}
                required
                value={address}
                maxLength={255}
                autoComplete="street-address"
                onChange={(event) => setAddress(event.target.value)}
              />
              <Input
                label={t("landmarks")}
                value={landmarks}
                maxLength={500}
                onChange={(event) => setLandmarks(event.target.value)}
              />
              <Input
                label={t("phone")}
                required
                type="tel"
                autoComplete="tel"
                value={phoneValue}
                onChange={(event) => setPhone(event.target.value)}
              />
            </fieldset>
          )}
          <Button type="submit" size="lg" fullWidth disabled={busy}>
            {t("toSummary")}
          </Button>
        </form>
      )}

      {step === 2 && quote && (
        <div className="flex flex-col gap-6">
          <Summary quote={quote} />
          <Button size="lg" fullWidth onClick={() => setStep(3)}>
            {t("toPayment")}
          </Button>
        </div>
      )}

      {step === 3 && quote && (
        <div className="flex flex-col gap-6">
          <ul className="flex flex-col gap-4">
            {[
              [<LockKey key="l" aria-hidden size={28} weight="duotone" />, t("held")],
              [<ShieldCheck key="s" aria-hidden size={28} weight="duotone" />, t("code")],
            ].map(([icon, text]) => (
              <li key={String(text)} className="bg-poudre flex items-start gap-3 rounded-2xl p-4">
                <span className="text-hibiscus shrink-0">{icon}</span>
                <span>{text}</span>
              </li>
            ))}
          </ul>
          <Button size="lg" fullWidth disabled={busy} onClick={() => void pay()}>
            <LockKey aria-hidden size={24} weight="bold" />
            {t("pay", { amount: formatMoney(quote.total_minor, quote.currency, locale) })}
          </Button>
        </div>
      )}
    </div>
  );
}
