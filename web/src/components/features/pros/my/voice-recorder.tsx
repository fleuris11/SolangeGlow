"use client";

import { Microphone, Stop } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";

const subscribe = () => () => {};
const supported = () =>
  typeof window !== "undefined" &&
  typeof window.MediaRecorder !== "undefined" &&
  !!navigator.mediaDevices?.getUserMedia;

/** Records a voice note with the phone's microphone, then hands it over. */
export function VoiceRecorder({ onRecorded }: { onRecorded: (file: Blob) => void }) {
  const t = useTranslations("pros.my.voice");
  const canRecord = useSyncExternalStore(subscribe, supported, () => false);
  const [seconds, setSeconds] = useState(0);
  const [recording, setRecording] = useState(false);
  const [denied, setDenied] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
      recorder.current?.stream.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  if (!canRecord) return null;

  const start = async () => {
    setDenied(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const media = new MediaRecorder(stream);
      media.ondataavailable = (event) => chunks.push(event.data);
      media.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        onRecorded(new Blob(chunks, { type: media.mimeType || "audio/webm" }));
      };
      recorder.current = media;
      media.start();
      setSeconds(0);
      setRecording(true);
      timer.current = setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch {
      setDenied(true);
    }
  };

  const stop = () => {
    recorder.current?.stop();
    if (timer.current) clearInterval(timer.current);
    setRecording(false);
  };

  return (
    <>
      {recording ? (
        <Button onClick={stop}>
          <Stop aria-hidden size={22} weight="fill" />
          {t("stop", { seconds })}
        </Button>
      ) : (
        <Button variant="secondary" onClick={() => void start()}>
          <Microphone aria-hidden size={22} weight="bold" />
          {t("record")}
        </Button>
      )}
      {denied && (
        <p role="alert" className="text-alerte text-small w-full font-bold">
          {t("denied")}
        </p>
      )}
    </>
  );
}
