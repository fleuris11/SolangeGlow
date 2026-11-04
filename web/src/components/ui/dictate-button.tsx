"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, useSyncExternalStore } from "react";

import { cn } from "@/lib/cn";
import { dictate, getRecognition } from "@/lib/voice/dictation";

const subscribe = () => () => {};

/**
 * « Speak » next to a text field: what is said is added to the text (module 11).
 * Icon drawn inline (a few bytes, no icon library on the phone).
 */
export function DictateButton({
  onText,
  className,
}: {
  onText: (text: string) => void;
  className?: string;
}) {
  const t = useTranslations("voice");
  const locale = useLocale();
  const [listening, setListening] = useState(false);
  const supported = useSyncExternalStore(
    subscribe,
    () => getRecognition() !== null,
    () => false,
  );
  if (!supported) return null;

  return (
    <button
      type="button"
      aria-pressed={listening}
      onClick={() => {
        setListening(true);
        dictate(
          locale,
          (text) => text && onText(text),
          () => setListening(false),
        );
      }}
      className={cn(
        "inline-flex min-h-12 shrink-0 items-center gap-1 rounded-full px-3 font-bold",
        listening ? "bg-rouge text-sur-hibiscus" : "bg-poudre text-prune",
        className,
      )}
    >
      <svg aria-hidden viewBox="0 0 256 256" width="20" height="20" fill="currentColor">
        <path d="M128 176a48 48 0 0 0 48-48V64a48 48 0 0 0-96 0v64a48 48 0 0 0 48 48Zm72-48a8 8 0 0 1 16 0 88.1 88.1 0 0 1-80 87.6V240a8 8 0 0 1-16 0v-24.4A88.1 88.1 0 0 1 40 128a8 8 0 0 1 16 0 72 72 0 0 0 144 0Z" />
      </svg>
      {listening ? t("listening") : t("speak")}
    </button>
  );
}

/** Adds dictated words after what is already written. */
export const appendText = (current: string, said: string) =>
  current.trim() ? `${current.trimEnd()} ${said}` : said;
