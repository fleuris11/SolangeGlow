"use client";

import { SpeakerHigh, Stop } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState, useSyncExternalStore } from "react";

import { cn } from "@/lib/cn";
import { usePreferences } from "@/lib/preferences/preferences-provider";
import { canSpeak, speak, stopSpeaking } from "@/lib/speech";

type Props = {
  /** The text read aloud. */
  text: string;
  /** Show even when the audio mode is off (e.g. the design catalogue). */
  always?: boolean;
  className?: string;
};

const subscribe = () => () => {};

/** Reads an important text aloud. Visible when the audio mode is on; hidden without speech API. */
export function SpeakButton({ text, always = false, className }: Props) {
  const t = useTranslations("audio");
  const locale = useLocale();
  const { audioMode } = usePreferences();
  const [speaking, setSpeaking] = useState(false);
  const supported = useSyncExternalStore(subscribe, canSpeak, () => false);

  useEffect(() => () => stopSpeaking(), []);

  if (!supported || (!audioMode && !always)) return null;

  const toggle = () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    speak(text, locale, () => setSpeaking(false));
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={speaking ? t("stop") : t("listenTo", { text })}
      className={cn(
        "text-small border-trait bg-carte text-prune hover:border-hibiscus inline-flex min-h-12 min-w-12 shrink-0 items-center justify-center gap-2 rounded-full border-2 px-3 font-bold",
        className,
      )}
    >
      {speaking ? (
        <Stop aria-hidden size={22} weight="fill" className="text-hibiscus" />
      ) : (
        <SpeakerHigh aria-hidden size={22} weight="duotone" className="text-hibiscus" />
      )}
      <span aria-hidden>{speaking ? t("stopShort") : t("listen")}</span>
    </button>
  );
}
