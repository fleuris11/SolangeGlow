/** Speech to text with the browser (free, no library). Hidden where it does not exist. */
export const VOICE_LANG: Record<string, string> = { fr: "fr-FR", en: "en-GB", sk: "sk-SK" };

type Recognition = {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type RecognitionConstructor = new () => Recognition;

export function getRecognition(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Listens once; `onText` gets what was said, `onEnd` is called in every case. */
export function dictate(locale: string, onText: (text: string) => void, onEnd: () => void) {
  const Recognition = getRecognition();
  if (!Recognition) return null;
  const recognition = new Recognition();
  recognition.lang = VOICE_LANG[locale] ?? locale;
  recognition.interimResults = false;
  recognition.onresult = (event) => onText(event.results[0]?.[0]?.transcript ?? "");
  recognition.onend = onEnd;
  recognition.onerror = onEnd;
  recognition.start();
  return recognition;
}
