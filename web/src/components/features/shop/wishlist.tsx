"use client";

import { Heart, Lightning } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getWishlist, wish } from "@/lib/api/shop";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

/** Products she loves: a price drop or a return in stock is announced. */
export function WishlistScreen() {
  const t = useTranslations("shop.wishlist");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["wishlist"], queryFn: getWishlist });

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  const rows = query.data?.results ?? [];
  if (rows.length === 0) {
    return (
      <EmptyState
        icon={<Heart size={44} weight="duotone" />}
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
  const remove = async (id: string) => {
    try {
      await wish(id, false);
      await queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      toast(t("removed"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <p className="text-prune-doux">{t("help")}</p>
      <ul className="flex flex-col gap-3">
        {rows.map((product) => (
          <li key={product.id} className="border-trait rounded-card flex gap-3 border p-3">
            <Link href={`/${product.shop_slug}/shop/${product.slug}`} className="flex flex-1 gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
              <img
                src={mediaSrc(product.photo, "thumb")}
                alt=""
                className="bg-poudre size-20 shrink-0 rounded-2xl object-cover"
              />
              <span className="flex min-w-0 flex-col gap-1">
                <span className="font-bold">{product.title}</span>
                <span className="font-bold">
                  {formatMoney(product.price_minor, product.currency, locale)}
                </span>
                {product.flash_sale && (
                  <span className="text-hibiscus text-small flex items-center gap-1 font-bold">
                    <Lightning aria-hidden size={16} weight="fill" />
                    {t("flash", { percent: product.flash_sale.percent_off })}
                  </span>
                )}
                {!product.in_stock && (
                  <span className="text-small text-alerte font-bold">{t("soldOut")}</span>
                )}
              </span>
            </Link>
            <Button
              variant="quiet"
              aria-label={t("remove", { title: product.title })}
              onClick={() => void remove(product.id)}
              className="self-start px-3"
            >
              <Heart aria-hidden size={22} weight="fill" className="text-hibiscus" />
              {t("removeShort")}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
