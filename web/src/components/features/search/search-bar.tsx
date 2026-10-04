"use client";

import { MagnifyingGlass, Microphone } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useState, useSyncExternalStore, type FormEvent } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import { useRouter } from "@/lib/i18n/navigation";

const VOICE_LANG: Record<string, string> = { fr: "fr-FR", en: "en-GB", sk: "sk-SK" };

type Recognition = {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
};

type RecognitionConstructor = new () => Recognition;

function getRecognition(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const subscribe = () => () => {};

/** Search a pro or a look, by typing or by voice ("tresses à Calavi"). */
export function SearchBar({ defaultValue = "" }: { defaultValue?: string }) {
  const t = useTranslations("search");
  const locale = useLocale();
  const router = useRouter();
  const [query, setQuery] = useState(defaultValue);
  const [listening, setListening] = useState(false);
  const voiceSupported = useSyncExternalStore(
    subscribe,
    () => getRecognition() !== null,
    () => false,
  );

  const go = (value: string) => {
    const q = value.trim();
    router.push(q ? { pathname: "/explore", query: { q } } : "/explore");
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    go(query);
  };

  const listen = () => {
    const Recognition = getRecognition();
    if (!Recognition) return;
    const recognition = new Recognition();
    recognition.lang = VOICE_LANG[locale] ?? locale;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setQuery(transcript);
      go(transcript);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    setListening(true);
    recognition.start();
  };

  return (
    <form role="search" onSubmit={onSubmit}>
      <Input
        type="search"
        name="q"
        label={t("label")}
        placeholder={t("placeholder")}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        enterKeyHint="search"
        leading={<MagnifyingGlass size={24} weight="bold" />}
        trailing={
          voiceSupported ? (
            <button
              type="button"
              onClick={listen}
              aria-pressed={listening}
              className={cn(
                "-mr-2 inline-flex min-h-11 shrink-0 items-center gap-1 rounded-full px-3 font-bold",
                listening ? "bg-hibiscus text-sur-hibiscus" : "bg-carte text-prune",
              )}
            >
              <Microphone aria-hidden size={22} weight={listening ? "fill" : "duotone"} />
              <span>{listening ? t("listening") : t("speak")}</span>
            </button>
          ) : null
        }
      />
    </form>
  );
}
