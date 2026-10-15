"use client";

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError, hasSession } from "@/lib/api/client";
import { addToCart, watchStock, wish, type ProductDetail } from "@/lib/api/shop";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { cn } from "@/lib/cn";
import { Link, usePathname, useRouter } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";
import { rememberPending, takePending, type PendingItem } from "@/lib/shop/pending";

/** Adds to the cart; a visitor signs in first and the item is added when she comes back. */
function useAdd() {
  const t = useTranslations("shop.buy");
  const toast = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const [busy, setBusy] = useState(false);
  const [added, setAdded] = useState(false);

  const add = async (item: PendingItem) => {
    if (!hasSession()) {
      rememberPending(item);
      rememberReturnPath(pathname);
      router.push("/auth");
      return;
    }
    setBusy(true);
    try {
      await addToCart(item);
      setAdded(true);
      toast(t("added"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };
  return { add, busy, added };
}

function CartLink() {
  const t = useTranslations("shop.buy");
  return (
    <Link href="/cart" className="text-hibiscus self-center font-bold underline">
      {t("seeCart")}
    </Link>
  );
}

/** « Add the bundle » on the shop page. */
export function BundleButton({
  bundleId,
  disabled,
  icon,
}: {
  bundleId: string;
  disabled: boolean;
  icon: ReactNode;
}) {
  const t = useTranslations("shop.buy");
  const { add, busy, added } = useAdd();
  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="secondary"
        disabled={disabled || busy}
        onClick={() => void add({ bundle_id: bundleId, quantity: 1 })}
      >
        {icon}
        {disabled ? t("soldOut") : t("addBundle")}
      </Button>
      {added && <CartLink />}
    </div>
  );
}

function useCountdown(endsAt: string | undefined) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    if (!endsAt) return;
    const tick = () => setNow(Date.now());
    const first = window.setTimeout(tick, 0);
    const timer = window.setInterval(tick, 30_000);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [endsAt]);
  if (!endsAt || now === null) return null;
  const left = Math.max(0, new Date(endsAt).getTime() - now);
  return { hours: Math.floor(left / 3_600_000), minutes: Math.floor((left % 3_600_000) / 60_000) };
}

type Icons = {
  cart: ReactNode;
  heart: ReactNode;
  heartFilled: ReactNode;
  bell: ReactNode;
  flash: ReactNode;
};

/** Choice of shade or size, quantity, price, countdown, cart, wishlist and stock alert. */
export function ProductBuy({
  product,
  locale,
  icons,
}: {
  product: ProductDetail;
  locale: string;
  icons: Icons;
}) {
  const t = useTranslations("shop.buy");
  const toast = useToast();
  const { add, busy, added } = useAdd();
  const variants = product.variants;
  const firstInStock = variants.find((v) => v.stock > 0) ?? variants[0];
  const [variantId, setVariantId] = useState(firstInStock?.id);
  const [quantity, setQuantity] = useState(1);
  const [wished, setWished] = useState(product.wished);
  const [watching, setWatching] = useState<string[]>(product.watching);
  const variant = variants.find((v) => v.id === variantId) ?? firstInStock;
  const countdown = useCountdown(product.flash_sale?.ends_at);
  const pending = useRef(false);
  const named = useMemo(() => variants.filter((v) => v.label), [variants]);

  // Back from the sign-in: the product she chose goes to the cart.
  useEffect(() => {
    if (pending.current || !hasSession()) return;
    pending.current = true;
    const item = takePending();
    if (item) void add(item);
    // Only once, when the page opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!variant) return null;
  const soldOut = variant.stock < 1;
  const closed = product.delivery !== null && !product.delivery.is_open;
  const isWatching = watching.includes(variant.id);

  const toggleWish = async () => {
    if (!hasSession()) {
      toast(t("signInFirst"), "info");
      return;
    }
    try {
      await wish(product.id, !wished);
      setWished(!wished);
      toast(wished ? t("unwished") : t("wished"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  const toggleWatch = async () => {
    if (!hasSession()) {
      toast(t("signInFirst"), "info");
      return;
    }
    try {
      await watchStock(variant.id, !isWatching);
      setWatching(
        isWatching ? watching.filter((id) => id !== variant.id) : [...watching, variant.id],
      );
      toast(isWatching ? t("unwatched") : t("watching"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <p className="flex flex-wrap items-baseline gap-x-3">
          <span className="text-headline font-bold">
            {formatMoney(variant.price_minor, product.currency, locale)}
          </span>
          {variant.before_minor !== null && (
            <s className="text-prune-doux text-lead">
              <span className="sr-only">{t("before")} </span>
              {formatMoney(variant.before_minor, product.currency, locale)}
            </s>
          )}
        </p>
        {product.flash_sale && (
          <p className="text-hibiscus flex items-center gap-2 font-bold" role="timer">
            {icons.flash}
            {countdown
              ? t("flashEnds", {
                  percent: product.flash_sale.percent_off,
                  hours: countdown.hours,
                  minutes: countdown.minutes,
                })
              : t("flash", { percent: product.flash_sale.percent_off })}
          </p>
        )}
      </div>

      {named.length > 0 && (
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 font-bold">
            {t("choose")} <span className="text-prune-doux font-normal">{variant.label}</span>
          </legend>
          <div className="flex flex-wrap gap-2">
            {named.map((option) => {
              const selected = option.id === variant.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => {
                    setVariantId(option.id);
                    setQuantity(1);
                  }}
                  className={cn(
                    "inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold",
                    selected ? "border-hibiscus bg-poudre" : "border-trait",
                    option.stock < 1 && "text-prune-doux",
                  )}
                >
                  {option.swatch && (
                    <span
                      aria-hidden
                      className="border-trait size-6 rounded-full border"
                      style={{ backgroundColor: option.swatch }}
                    />
                  )}
                  {option.label}
                  {option.stock < 1 && <span className="sr-only">{t("soldOut")}</span>}
                </button>
              );
            })}
          </div>
        </fieldset>
      )}

      {!soldOut && (
        <div className="flex items-center gap-4">
          <span className="font-bold" id="quantity-label">
            {t("quantity")}
          </span>
          <div role="group" aria-labelledby="quantity-label" className="flex items-center gap-2">
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
              disabled={quantity >= variant.stock}
              onClick={() => setQuantity(quantity + 1)}
              className="min-w-12 px-0"
            >
              +
            </Button>
          </div>
          {variant.stock <= 3 && (
            <span className="text-small text-alerte font-bold">
              {t("fewLeft", { count: variant.stock })}
            </span>
          )}
        </div>
      )}

      {product.is_mine ? (
        <p className="bg-poudre rounded-2xl p-3">{t("yours")}</p>
      ) : soldOut ? (
        <div className="flex flex-col gap-2">
          <p className="text-alerte font-bold">{t("soldOut")}</p>
          <Button
            size="lg"
            fullWidth
            variant={isWatching ? "secondary" : "primary"}
            onClick={() => void toggleWatch()}
          >
            {icons.bell}
            {isWatching ? t("stopWatching") : t("tellMe")}
          </Button>
        </div>
      ) : (
        <Button
          size="lg"
          fullWidth
          disabled={busy || closed}
          onClick={() => void add({ variant_id: variant.id, quantity })}
        >
          {icons.cart}
          {closed
            ? t("closed")
            : t("add", {
                price: formatMoney(variant.price_minor * quantity, product.currency, locale),
              })}
        </Button>
      )}
      {added && <CartLink />}
      {!product.is_mine && (
        <Button variant="quiet" aria-pressed={wished} onClick={() => void toggleWish()}>
          {wished ? icons.heartFilled : icons.heart}
          {wished ? t("inWishlist") : t("wish")}
        </Button>
      )}
    </div>
  );
}
