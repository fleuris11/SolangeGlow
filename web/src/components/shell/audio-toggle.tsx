"use client";

import { SpeakerHigh, SpeakerSlash } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";
import { usePreferences } from "@/lib/preferences/preferences-provider";

/** Turns the audio mode on or off: speaker buttons appear next to important texts. */
export function AudioToggle({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
  const t = useTranslations("audio");
  const { audioMode, update } = usePreferences();

  return (
    <button
      type="button"
      aria-pressed={audioMode}
      onClick={() => update({ audioMode: !audioMode })}
      className={cn(
        "inline-flex min-h-12 shrink-0 items-center font-bold",
        compact
          ? "text-mention min-w-14 flex-col justify-center rounded-2xl px-2"
          : "gap-1 rounded-full px-3",
        audioMode ? "bg-prune text-lait" : "hover:bg-poudre",
        className,
      )}
    >
      {audioMode ? (
        <SpeakerHigh aria-hidden size={compact ? 24 : 22} weight="fill" />
      ) : (
        <SpeakerSlash aria-hidden size={compact ? 24 : 22} weight="duotone" />
      )}
      <span>{t("mode")}</span>
    </button>
  );
}
