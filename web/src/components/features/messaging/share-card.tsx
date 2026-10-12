"use client";

import { CalendarCheck, Image as ImageIcon, Scissors, ShoppingBag } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";

import type { ShareCard as Card } from "@/lib/api/messaging";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

const ICONS = { post: ImageIcon, service: Scissors, slot: CalendarCheck, product: ShoppingBag };

/** A shared post, service, free slot or product: picture, title, details, a link. */
export function ShareCardView({ card, mine = false }: { card: Card; mine?: boolean }) {
  const t = useTranslations("messages.card");
  const locale = useLocale();
  const Icon = ICONS[card.kind];
  const picture = mediaSrc(card.picture, "thumb", "medium");
  const details =
    card.kind === "slot" && card.starts_at
      ? new Intl.DateTimeFormat(locale, { dateStyle: "full", timeStyle: "short" }).format(
          new Date(card.starts_at),
        )
      : card.kind === "service"
        ? card.price_kind === "quote" || card.amount_minor == null
          ? t("quote")
          : t(card.price_kind === "from" ? "priceFrom" : "price", {
              price: formatMoney(card.amount_minor, card.currency ?? "XOF", locale),
            })
        : card.text;

  return (
    <Link
      href={card.link}
      className={cn(
        "rounded-card flex min-h-16 items-center gap-3 overflow-hidden border p-2",
        mine ? "border-sur-hibiscus/40 bg-carte text-prune" : "border-trait bg-carte",
      )}
    >
      {picture ? (
        // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
        <img src={picture} alt="" className="size-14 shrink-0 rounded-xl object-cover" />
      ) : (
        <span className="bg-poudre text-hibiscus inline-flex size-14 shrink-0 items-center justify-center rounded-xl">
          <Icon aria-hidden size={28} weight="duotone" />
        </span>
      )}
      <span className="flex min-w-0 flex-col">
        <span className="text-mention text-prune-doux flex items-center gap-1 font-bold">
          <Icon aria-hidden size={16} weight="bold" />
          {t(`kinds.${card.kind}`)}
        </span>
        <span className="truncate font-bold">{card.title}</span>
        {details && <span className="text-small line-clamp-2">{details}</span>}
      </span>
    </Link>
  );
}
