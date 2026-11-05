"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";
import { usePreferences } from "@/lib/preferences/preferences-provider";

// One weight drawn here: this button is on every page, and a client icon carries all six (ADR-004).
const SPEAKER_ON =
  "M155.51,24.81a8,8,0,0,0-8.42.88L77.25,80H32A16,16,0,0,0,16,96v64a16,16,0,0,0,16,16H77.25l69.84,54.31A8,8,0,0,0,160,224V32A8,8,0,0,0,155.51,24.81ZM32,96H72v64H32ZM144,207.64,88,164.09V91.91l56-43.55Zm54-106.08a40,40,0,0,1,0,52.88,8,8,0,0,1-12-10.58,24,24,0,0,0,0-31.72,8,8,0,0,1,12-10.58ZM248,128a79.9,79.9,0,0,1-20.37,53.34,8,8,0,0,1-11.92-10.67,64,64,0,0,0,0-85.33,8,8,0,1,1,11.92-10.67A79.83,79.83,0,0,1,248,128Z";
const SPEAKER_OFF =
  "M53.92,34.62A8,8,0,1,0,42.08,45.38L73.55,80H32A16,16,0,0,0,16,96v64a16,16,0,0,0,16,16H77.25l69.84,54.31A8,8,0,0,0,160,224V175.09l42.08,46.29a8,8,0,1,0,11.84-10.76ZM32,96H72v64H32ZM144,207.64,88,164.09V95.89l56,61.6Zm42-63.77a24,24,0,0,0,0-31.72,8,8,0,1,1,12-10.57,40,40,0,0,1,0,52.88,8,8,0,0,1-12-10.59Zm-80.16-76a8,8,0,0,1,1.4-11.23l39.85-31A8,8,0,0,1,160,32v74.83a8,8,0,0,1-16,0V48.36l-26.94,21A8,8,0,0,1,105.84,67.91ZM248,128a79.9,79.9,0,0,1-20.37,53.34,8,8,0,0,1-11.92-10.67,64,64,0,0,0,0-85.33,8,8,0,1,1,11.92-10.67A79.83,79.83,0,0,1,248,128Z";

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
          ? "text-mention rounded-button min-w-14 flex-col justify-center px-2"
          : "gap-1 rounded-full px-3",
        audioMode ? "bg-prune text-lait" : "hover:bg-poudre",
        className,
      )}
    >
      <svg
        aria-hidden
        width={compact ? 24 : 22}
        height={compact ? 24 : 22}
        viewBox="0 0 256 256"
        fill="currentColor"
      >
        <path d={audioMode ? SPEAKER_ON : SPEAKER_OFF} />
      </svg>
      <span>{t("mode")}</span>
    </button>
  );
}
