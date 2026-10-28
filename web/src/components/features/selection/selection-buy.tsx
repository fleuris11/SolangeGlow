"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError, hasSession } from "@/lib/api/client";
import { placeSelectionOrder, type PickupPoint, type SelectionProduct } from "@/lib/api/selection";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { cn } from "@/lib/cn";
import { Link, usePathname, useRouter } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

import { shortDate } from "./dates";

type Way = "grouped" | "express" | "group";

function Choice({
  name,
  selected,
  onSelect,
  children,
}: {
  name: string;
  selected: boolean;
  onSelect: () => void;
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

function useTimeLeft(endsAt: string | undefined) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    if (!endsAt) return;
    const tick = () => setNow(Date.now());
    const first = window.setTimeout(tick, 0);
    const timer = window.setInterval(tick, 60_000);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [endsAt]);
  if (!endsAt || now === null) return null;
  const left = Math.max(0, new Date(endsAt).getTime() - now);
  return {
    days: Math.floor(left / 86_400_000),
    hours: Math.floor((left % 86_400_000) / 3_600_000),
  };
}

/** Choice, quantity, shipping (with its price and delay), pick-up point, then payment. */
export function SelectionBuy({
  product,
  points,
  icons,
}: {
  product: SelectionProduct;
  points: PickupPoint[];
  icons: { lock: ReactNode; gift?: ReactNode };
}) {
  const t = useTranslations("selection.buy");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const group = product.group;
  const [way, setWay] = useState<Way>(group ? "group" : "grouped");
  const [option, setOption] = useState(product.options[0] ?? "");
  const [quantity, setQuantity] = useState(1);
  const [point, setPoint] = useState(points[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const timeLeft = useTimeLeft(group?.ends_at);
  const money = (value: number) => formatMoney(value, "XOF", locale);
  const range = (estimate: { from: string; to: string }) =>
    t("between", { from: shortDate(estimate.from, locale), to: shortDate(estimate.to, locale) });

  const unit =
    way === "group" && group
      ? group.price_xof
      : way === "express" && product.express_price_xof !== null
        ? product.express_price_xof
        : product.price_xof;

  const pay = async () => {
    if (!hasSession()) {
      rememberReturnPath(pathname);
      router.push("/auth");
      return;
    }
    setBusy(true);
    try {
      const order = await placeSelectionOrder({
        product_id: product.id,
        shipping_mode: way === "express" ? "express" : "grouped",
        pickup_point_id: point,
        option,
        quantity,
        group: way === "group",
      });
      window.location.assign(order.payment?.checkout_url || `/selection/orders/${order.id}`);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      setBusy(false);
    }
  };

  if (!product.available) {
    return <p className="bg-poudre rounded-2xl p-3 font-bold">{t("unavailable")}</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      {group && (
        <section aria-labelledby="group" className="bg-poudre rounded-card flex flex-col gap-2 p-4">
          <h2 id="group" className="font-bold">
            {t("groupTitle", { price: money(group.price_xof), before: money(product.price_xof) })}
          </h2>
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={group.target}
            aria-valuenow={Math.min(group.count, group.target)}
            aria-label={t("groupProgress", { count: group.count, target: group.target })}
            className="bg-carte h-3 overflow-hidden rounded-full"
          >
            <div
              className="bg-hibiscus h-full rounded-full"
              style={{ width: `${Math.min(100, (group.count / group.target) * 100)}%` }}
            />
          </div>
          <p className="text-small">
            {t("groupProgress", { count: group.count, target: group.target })}
            {timeLeft && ` ${t("groupLeft", { days: timeLeft.days, hours: timeLeft.hours })}`}
          </p>
          <p className="text-small text-prune-doux">{t("groupHelp")}</p>
        </section>
      )}

      {product.options.length > 0 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-bold">{t("choose")}</legend>
          <div className="flex flex-wrap gap-2">
            {product.options.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={option === value}
                onClick={() => setOption(value)}
                className={cn(
                  "min-h-12 rounded-full border-2 px-4 font-bold",
                  option === value ? "border-hibiscus bg-poudre" : "border-trait",
                )}
              >
                {value}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      <div className="flex items-center gap-4">
        <span className="font-bold" id="selection-quantity">
          {t("quantity")}
        </span>
        <div role="group" aria-labelledby="selection-quantity" className="flex items-center gap-2">
          <Button
            variant="secondary"
            aria-label={t("less")}
            disabled={quantity <= 1}
            onClick={() => setQuantity(quantity - 1)}
            className="min-w-12 px-0"
          >
            −
          </Button>
          <output aria-live="polite" className="text-lead min-w-8 text-center font-bold">
            {quantity}
          </output>
          <Button
            variant="secondary"
            aria-label={t("more")}
            disabled={quantity >= 5}
            onClick={() => setQuantity(quantity + 1)}
            className="min-w-12 px-0"
          >
            +
          </Button>
        </div>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">{t("shipping")}</legend>
        {group && product.estimates.group && (
          <Choice name="way" selected={way === "group"} onSelect={() => setWay("group")}>
            <span className="flex flex-1 flex-col">
              <span className="font-bold">{t("wayGroup")}</span>
              <span className="text-small text-prune-doux">{range(product.estimates.group)}</span>
            </span>
            <span className="font-bold">{money(group.price_xof)}</span>
          </Choice>
        )}
        <Choice name="way" selected={way === "grouped"} onSelect={() => setWay("grouped")}>
          <span className="flex flex-1 flex-col">
            <span className="font-bold">{t("wayGrouped")}</span>
            <span className="text-small text-prune-doux">{range(product.estimates.grouped)}</span>
          </span>
          <span className="font-bold">{money(product.price_xof)}</span>
        </Choice>
        {product.express_price_xof !== null && (
          <Choice name="way" selected={way === "express"} onSelect={() => setWay("express")}>
            <span className="flex flex-1 flex-col">
              <span className="font-bold">{t("wayExpress")}</span>
              <span className="text-small text-prune-doux">{range(product.estimates.express)}</span>
            </span>
            <span className="font-bold">{money(product.express_price_xof)}</span>
          </Choice>
        )}
        {product.category.air_restricted && (
          <p className="text-small text-prune-doux">{t("noExpress")}</p>
        )}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">{t("pickup")}</legend>
        {points.map((item) => (
          <Choice
            key={item.id}
            name="point"
            selected={point === item.id}
            onSelect={() => setPoint(item.id)}
          >
            <span className="flex flex-col">
              <span className="font-bold">{item.name}</span>
              <span className="text-small text-prune-doux">
                {[item.address, item.city].filter(Boolean).join(", ")}
              </span>
              {item.hours && <span className="text-small text-prune-doux">{item.hours}</span>}
            </span>
          </Choice>
        ))}
      </fieldset>

      <p className="text-small text-prune-doux">{t("final")}</p>
      <Button size="lg" fullWidth disabled={busy || !point} onClick={() => void pay()}>
        {icons.lock}
        {t("pay", { amount: money(unit * quantity) })}
      </Button>
      <Link
        href={`/offrir?kind=selection&selection_product=${product.id}${
          option ? `&option=${encodeURIComponent(option)}` : ""
        }`}
        className={buttonClasses({ variant: "secondary", fullWidth: true })}
      >
        {icons.gift}
        {t("offer")}
      </Link>
    </div>
  );
}
