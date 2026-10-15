"use client";

import { ShoppingBag, Storefront, Trash, Warning } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getCart, removeFromCart, setCartQuantity, type Cart } from "@/lib/api/shop";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

export const CART_KEY = ["cart"];

/** The cart: one block per shop, the checkout opens for all the shops that can sell. */
export function CartScreen() {
  const t = useTranslations("shop.cart");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: CART_KEY, queryFn: getCart });
  const [busy, setBusy] = useState(false);

  const change = async (step: () => Promise<Cart>) => {
    setBusy(true);
    try {
      queryClient.setQueryData(CART_KEY, await step());
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (query.isError || !query.data) {
    return (
      <p role="alert" className="font-bold">
        {t("error")}
      </p>
    );
  }
  const cart = query.data;
  if (cart.shops.length === 0) {
    return (
      <EmptyState
        icon={<ShoppingBag size={44} weight="duotone" />}
        title={t("empty")}
        description={t("emptyHelp")}
        action={
          <Link href="/explore" className={buttonClasses({ size: "lg" })}>
            {t("explore")}
          </Link>
        }
      />
    );
  }
  const ready = cart.shops.filter(
    (shop) =>
      shop.delivery.is_open && shop.lines.every((l) => l.available && l.stock_left >= l.quantity),
  );
  // One payment per currency: the checkout takes the shops of the first one.
  const currency = ready[0]?.currency ?? cart.shops[0]?.currency ?? "XOF";
  const sameCurrency = ready.every((shop) => shop.currency === currency);
  const total = ready
    .filter((shop) => shop.currency === currency)
    .reduce((sum, shop) => sum + shop.subtotal_minor, 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={t("title")} />
      </div>
      {cart.shops.map((shop) => (
        <section
          key={shop.pro_id}
          aria-labelledby={`shop-${shop.pro_id}`}
          className="border-trait rounded-card flex flex-col gap-3 border p-4"
        >
          <h2 id={`shop-${shop.pro_id}`} className="text-lead flex items-center gap-2 font-bold">
            <Storefront aria-hidden size={24} weight="duotone" className="text-hibiscus" />
            {shop.shop.name}
          </h2>
          {!shop.delivery.is_open && <p className="text-alerte font-bold">{t("closed")}</p>}
          <ul className="flex flex-col gap-4">
            {shop.lines.map((line) => {
              const short = !line.available || line.stock_left < line.quantity;
              return (
                <li key={line.id} className="flex gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
                  <img
                    src={mediaSrc(line.photo, "thumb", "medium")}
                    alt=""
                    className="bg-poudre size-20 shrink-0 rounded-2xl object-cover"
                  />
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <p className="font-bold">{line.title}</p>
                    {line.variant_label && (
                      <p className="text-small text-prune-doux">{line.variant_label}</p>
                    )}
                    <p className="font-bold">
                      {formatMoney(line.total_minor, shop.currency, locale)}
                    </p>
                    {short && (
                      <p className="text-small text-alerte flex items-center gap-1 font-bold">
                        <Warning aria-hidden size={18} />
                        {line.available ? t("onlyLeft", { count: line.stock_left }) : t("gone")}
                      </p>
                    )}
                    <div className="flex items-center gap-2">
                      <label className="sr-only" htmlFor={`qty-${line.id}`}>
                        {t("quantity", { title: line.title })}
                      </label>
                      <select
                        id={`qty-${line.id}`}
                        value={line.quantity}
                        disabled={busy}
                        onChange={(event) =>
                          void change(() => setCartQuantity(line.id, Number(event.target.value)))
                        }
                        className="rounded-field bg-poudre min-h-12 px-3 font-bold"
                      >
                        {Array.from(
                          { length: Math.max(line.quantity, Math.min(line.stock_left, 20)) },
                          (_, i) => i + 1,
                        ).map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                      <Button
                        variant="quiet"
                        disabled={busy}
                        onClick={() => void change(() => removeFromCart(line.id))}
                      >
                        <Trash aria-hidden size={20} />
                        {t("remove")}
                      </Button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="flex justify-between font-bold">
            <span>{t("subtotal")}</span>
            <span>{formatMoney(shop.subtotal_minor, shop.currency, locale)}</span>
          </p>
        </section>
      ))}
      <p className="text-small text-prune-doux">{t("protection")}</p>
      {!sameCurrency && <p className="bg-poudre rounded-2xl p-3">{t("twoCurrencies")}</p>}
      {ready.length > 0 ? (
        <Link href="/checkout" className={buttonClasses({ size: "lg", fullWidth: true })}>
          {t("checkout", { amount: formatMoney(total, currency, locale) })}
        </Link>
      ) : (
        <p className="text-alerte font-bold">{t("nothingReady")}</p>
      )}
    </div>
  );
}
