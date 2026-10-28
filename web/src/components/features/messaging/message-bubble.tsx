"use client";

import {
  ArrowClockwise,
  Check,
  Checks,
  Clock,
  Flag,
  Robot,
  ShieldWarning,
  Trash,
  WarningCircle,
} from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { SpeakButton } from "@/components/ui/speak-button";
import type { Message } from "@/lib/api/messaging";
import { cn } from "@/lib/cn";
import { mediaSrc, voiceSrc } from "@/lib/media";

import { CallLine } from "./call-line";
import { ShareCardView } from "./share-card";

export type Delivery = "waiting" | "failed" | "sent" | "received" | "read";

type Props = {
  message: Message;
  mine: boolean;
  /** Shown under her last message only. */
  delivery?: Delivery;
  onDelete?: () => void;
  onReport?: () => void;
  onRetry?: () => void;
};

function DeliveryLine({ delivery }: { delivery: Delivery }) {
  const t = useTranslations("messages.delivery");
  const icons = {
    waiting: Clock,
    failed: WarningCircle,
    sent: Check,
    received: Checks,
    read: Checks,
  } as const;
  const Icon = icons[delivery];
  return (
    <span
      className={cn(
        "text-mention flex items-center justify-end gap-1 font-bold",
        delivery === "failed" ? "text-alerte" : "text-prune-doux",
      )}
    >
      <Icon
        aria-hidden
        size={16}
        weight="bold"
        className={delivery === "read" ? "text-hibiscus" : undefined}
      />
      {t(delivery)}
    </span>
  );
}

/** One message: her own on the right, the others on the left; tap for its actions. */
export function MessageBubble({ message, mine, delivery, onDelete, onReport, onRetry }: Props) {
  const t = useTranslations("messages.thread");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const time = new Intl.DateTimeFormat(locale, { timeStyle: "short" }).format(
    new Date(message.created_at),
  );

  if (message.kind === "call" && message.call) {
    return <CallLine call={message.call} mine={mine} time={time} />;
  }

  if (message.kind === "system") {
    return (
      <p className="text-small text-prune-doux bg-poudre mx-auto max-w-[85%] rounded-full px-4 py-2 text-center">
        {message.text}
      </p>
    );
  }

  const gone = message.state === "deleted" || message.state === "removed";
  const picture = mediaSrc(message.media, "medium", "thumb");
  const voice = voiceSrc(message.media);
  const actionable = !gone && (mine ? !!onDelete : !!onReport);

  const body = gone ? (
    <p className="italic">{t(message.state === "deleted" ? "deleted" : "removed")}</p>
  ) : (
    <>
      {message.share && <ShareCardView card={message.share} mine={mine} />}
      {message.kind === "photo" && picture && (
        // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
        <img
          src={picture}
          alt={message.text || t("photo")}
          loading="lazy"
          className="max-h-80 w-full rounded-2xl object-cover"
        />
      )}
      {message.kind === "voice" && voice && (
        <audio controls preload="none" src={voice} className="w-60 max-w-full">
          <track kind="captions" />
        </audio>
      )}
      {message.text && <p className="break-words whitespace-pre-line">{message.text}</p>}
    </>
  );

  return (
    <div className={cn("flex flex-col gap-1", mine ? "items-end" : "items-start")}>
      {message.is_automatic && (
        <span className="text-mention text-prune-doux flex items-center gap-1 font-bold">
          <Robot aria-hidden size={16} weight="bold" />
          {t("automatic")}
        </span>
      )}
      <div
        className={cn(
          "flex max-w-[85%] flex-col gap-2 rounded-3xl px-4 py-3",
          mine
            ? "bg-hibiscus text-sur-hibiscus rounded-br-md"
            : "bg-carte border-trait rounded-bl-md border",
          message.state === "held" && "opacity-70",
        )}
      >
        {body}
        <span className={cn("text-mention", mine ? "text-sur-hibiscus" : "text-prune-doux")}>
          {time}
        </span>
      </div>
      {!mine && message.fraud_labels.length > 0 && !gone && (
        <p className="text-small text-alerte flex max-w-[85%] items-start gap-1 font-bold">
          <ShieldWarning aria-hidden size={18} weight="fill" className="shrink-0" />
          {t("risky")}
        </p>
      )}
      {message.state === "held" && mine && (
        <p className="text-small text-prune-doux">{t("held")}</p>
      )}
      <div className="flex flex-wrap items-center justify-end gap-1">
        {!mine && !gone && message.kind === "text" && <SpeakButton text={message.text} />}
        {actionable && (
          <Button variant="quiet" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
            {mine ? <Trash aria-hidden size={18} /> : <Flag aria-hidden size={18} />}
            {mine ? t("delete") : t("report")}
          </Button>
        )}
      </div>
      {open && (
        <div className="bg-poudre rounded-card flex max-w-[85%] flex-col gap-2 p-3">
          <p className="text-small">{mine ? t("deleteConfirm") : t("reportConfirm")}</p>
          <Button
            onClick={() => {
              setOpen(false);
              (mine ? onDelete : onReport)?.();
            }}
          >
            {mine ? t("deleteYes") : t("reportYes")}
          </Button>
        </div>
      )}
      {delivery && <DeliveryLine delivery={delivery} />}
      {delivery === "failed" && onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          <ArrowClockwise aria-hidden size={18} weight="bold" />
          {t("retry")}
        </Button>
      )}
    </div>
  );
}
