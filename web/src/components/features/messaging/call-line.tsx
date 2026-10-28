"use client";

import { Phone, PhoneSlash, VideoCamera } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import type { Message } from "@/lib/api/messaging";
import { cn } from "@/lib/cn";

type CallLineData = NonNullable<Message["call"]>;

/** « Video call, 3 min », « Missed call »: a line of the call log in the conversation. */
export function CallLine({
  call,
  mine,
  time,
}: {
  call: CallLineData;
  mine: boolean;
  time: string;
}) {
  const t = useTranslations("calls.line");
  const missed = call.status !== "ended";
  const Icon = missed ? PhoneSlash : call.kind === "video" ? VideoCamera : Phone;
  const minutes = Math.max(1, Math.round(call.duration_seconds / 60));
  const label = missed
    ? t(mine ? "noAnswer" : "missed")
    : t(call.kind === "video" ? "video" : "audio", { minutes });
  return (
    <p
      className={cn(
        "text-small bg-poudre mx-auto flex max-w-[85%] items-center gap-2 rounded-full px-4 py-2 font-bold",
        missed && !mine && "text-alerte",
      )}
    >
      <Icon aria-hidden size={20} weight="bold" className="shrink-0" />
      <span>{label}</span>
      <span className="text-prune-doux font-normal">{time}</span>
    </p>
  );
}
