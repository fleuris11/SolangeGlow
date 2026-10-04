const VOICE_LANG: Record<string, string> = { fr: "fr-FR", en: "en-GB", sk: "sk-SK" };

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/** Reads a text aloud with the browser voice of the current language. */
export function speak(text: string, locale: string, onEnd?: () => void): void {
  if (!canSpeak()) return;
  const synth = window.speechSynthesis;
  synth.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  const lang = VOICE_LANG[locale] ?? locale;
  utterance.lang = lang;
  const voice = synth.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2)));
  if (voice) utterance.voice = voice;
  utterance.rate = 0.95;
  if (onEnd) {
    utterance.onend = onEnd;
    utterance.onerror = onEnd;
  }
  synth.speak(utterance);
}

export function stopSpeaking(): void {
  if (canSpeak()) window.speechSynthesis.cancel();
}
