"use client";

import { WarningCircle } from "@phosphor-icons/react";
import { useLocale } from "next-intl";
import { useEffect } from "react";

import { SpeakButton } from "@/components/ui/speak-button";
import { usePreferences } from "@/lib/preferences/preferences-provider";
import { speak } from "@/lib/speech";

/** What went wrong and what to do; read aloud at once when the audio mode is on. */
export function ErrorMessage({ message }: { message?: string }) {
  const locale = useLocale();
  const { audioMode } = usePreferences();

  useEffect(() => {
    if (message && audioMode) speak(message, locale);
  }, [message, audioMode, locale]);

  if (!message) return null;
  return (
    <div
      role="alert"
      className="border-alerte bg-carte rounded-card flex items-start gap-3 border-2 p-4"
    >
      <WarningCircle aria-hidden size={28} weight="fill" className="text-alerte mt-0.5 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <p className="font-bold">{message}</p>
        <SpeakButton text={message} always />
      </div>
    </div>
  );
}
