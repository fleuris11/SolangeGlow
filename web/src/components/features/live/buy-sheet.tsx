"use client";

import { ShoppingBag } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { PriceTag } from "@/components/ui/price-tag";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import type { LivePin } from "@/lib/api/live";
import { addToCart, getProduct } from "@/lib/api/shop";
import { cn } from "@/lib/cn";

/**
 * Buying during the live: the variant, the cart, then the payment in a new tab (the live
 * keeps playing here). The cart line remembers the live: the live counts its sales.
 */
export function BuySheet({
  pin,
  liveId,
  signedIn,
  onClose,
  onSignIn,
}: {
  pin: LivePin;
  liveId: string;
  signedIn: boolean;
  onClose: () => void;
  onSignIn: () => void;
}) {
  const t = useTranslations("live.buy");
  const locale = useLocale();
  const toast = useToast();
  const [variantId, setVariantId] = useState<string | null>(null);
  const [added, setAdded] = useState(false);
  const [busy, setBusy] = useState(false);
  const product = useQuery({
    queryKey: ["shop-product", pin.product_id],
    queryFn: () => getProduct(pin.product_id),
  });
  const variants = (product.data?.variants ?? []).filter((v) => v.is_active);
  // The first shade in stock is chosen at first, like on the product page.
  const chosen =
    variants.find((v) => v.id === variantId) ?? variants.find((v) => v.stock > 0) ?? variants[0];

  const add = async () => {
    if (!chosen) return;
    setBusy(true);
    try {
      await addToCart({ variant_id: chosen.id, quantity: 1, sale_live_id: liveId });
      setAdded(true);
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()} title={pin.name}>
      {product.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : added ? (
        <div className="flex flex-col gap-4">
          <p className="text-title font-bold" role="status">
            {t("added")}
          </p>
          <p className="text-prune-doux">{t("keepWatching")}</p>
          <a
            href={`/${locale}/checkout`}
            target="_blank"
            rel="noopener"
            className={buttonClasses({ size: "lg", fullWidth: true })}
          >
            <ShoppingBag aria-hidden size={24} weight="bold" />
            {t("pay")}
          </a>
          <Button variant="quiet" fullWidth onClick={onClose}>
            {t("backToLive")}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <PriceTag
            amountMinor={chosen?.price_minor ?? pin.price_minor}
            currency={pin.currency}
            size="lg"
          />
          {variants.length > 1 && (
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-2 font-bold">{t("choose")}</legend>
              <div className="flex flex-wrap gap-2">
                {variants.map((variant) => (
                  <button
                    key={variant.id}
                    type="button"
                    aria-pressed={chosen?.id === variant.id}
                    disabled={variant.stock <= 0}
                    onClick={() => setVariantId(variant.id)}
                    className={cn(
                      "min-h-12 rounded-full border-2 px-4 font-bold disabled:opacity-50",
                      chosen?.id === variant.id
                        ? "border-hibiscus bg-poudre"
                        : "border-trait bg-carte",
                    )}
                  >
                    {variant.label}
                  </button>
                ))}
              </div>
            </fieldset>
          )}
          {!pin.in_stock && <p className="text-alerte font-bold">{t("soldOut")}</p>}
          {signedIn ? (
            <Button
              size="lg"
              fullWidth
              disabled={busy || !chosen || !pin.in_stock || (chosen?.stock ?? 0) <= 0}
              onClick={() => void add()}
            >
              <ShoppingBag aria-hidden size={24} weight="bold" />
              {t("add")}
            </Button>
          ) : (
            <Button size="lg" fullWidth onClick={onSignIn}>
              {t("signIn")}
            </Button>
          )}
        </div>
      )}
    </Sheet>
  );
}
