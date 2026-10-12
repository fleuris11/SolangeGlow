"use client";

import { Microphone, PaperPlaneRight, X } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

const subscribe = () => () => {};
const supported = () =>
  typeof window !== "undefined" &&
  typeof window.MediaRecorder !== "undefined" &&
  !!navigator.mediaDevices?.getUserMedia;

// Shorter than this, a press is a tap: recording goes on with « Send » and « Cancel » buttons
// (keyboards, screen readers and people who cannot hold a button).
const TAP_MS = 450;

type Mode = "idle" | "holding" | "open";

/** Hold to talk, release to send, slide away to cancel. A tap opens the button version. */
export function HoldToRecord({ onRecorded }: { onRecorded: (file: Blob) => void }) {
  const t = useTranslations("messages.voice");
  const canRecord = useSyncExternalStore(subscribe, supported, () => false);
  const [mode, setMode] = useState<Mode>("idle");
  const [seconds, setSeconds] = useState(0);
  const [denied, setDenied] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const keep = useRef(true);
  const startedAt = useRef(0);
  // Released before the microphone was ready (permission prompt): it was a tap.
  const released = useRef(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
      keep.current = false;
      recorder.current?.stream.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  if (!canRecord) return null;

  const start = async (next: Mode) => {
    setDenied(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const media = new MediaRecorder(stream);
      media.ondataavailable = (event) => chunks.push(event.data);
      media.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        if (keep.current && chunks.length) {
          onRecorded(new Blob(chunks, { type: media.mimeType || "audio/webm" }));
        }
      };
      recorder.current = media;
      keep.current = true;
      media.start();
      startedAt.current = Date.now();
      setSeconds(0);
      setMode(next === "holding" && released.current ? "open" : next);
      timer.current = setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch {
      setDenied(true);
      setMode("idle");
    }
  };

  const finish = (send: boolean) => {
    keep.current = send;
    if (timer.current) clearInterval(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
    recorder.current = null;
    setMode("idle");
  };

  const clock = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

  if (mode === "open") {
    return (
      <div className="flex w-full items-center gap-2" role="group" aria-label={t("recording")}>
        <span className="text-alerte flex flex-1 items-center gap-2 font-bold" aria-live="polite">
          <span aria-hidden className="bg-alerte size-3 animate-pulse rounded-full" />
          {t("recordingFor", { time: clock })}
        </span>
        <Button variant="quiet" onClick={() => finish(false)}>
          <X aria-hidden size={20} weight="bold" />
          {t("cancel")}
        </Button>
        <Button onClick={() => finish(true)}>
          <PaperPlaneRight aria-hidden size={20} weight="bold" />
          {t("send")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      {mode === "holding" && (
        <p className="text-small text-alerte font-bold" aria-live="polite">
          {t("holding", { time: clock })}
        </p>
      )}
      <button
        type="button"
        aria-label={t("hold")}
        className={cn(
          "inline-flex size-12 shrink-0 touch-none items-center justify-center rounded-full select-none",
          mode === "holding" ? "bg-alerte text-lait scale-110" : "bg-poudre text-prune",
        )}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          event.currentTarget.setPointerCapture(event.pointerId);
          released.current = false;
          void start("holding");
        }}
        onPointerUp={() => {
          released.current = true;
          if (!recorder.current) return;
          if (Date.now() - startedAt.current < TAP_MS) {
            setMode("open");
            return;
          }
          finish(true);
        }}
        onPointerCancel={() => finish(false)}
        onPointerLeave={(event) => {
          // Sliding the finger away cancels.
          if (mode === "holding" && event.pointerType !== "mouse") finish(false);
        }}
        onKeyDown={(event) => {
          if ((event.key === "Enter" || event.key === " ") && mode === "idle") {
            event.preventDefault();
            void start("open");
          }
        }}
      >
        <Microphone aria-hidden size={26} weight="bold" />
      </button>
      {denied && (
        <p role="alert" className="text-alerte text-small font-bold">
          {t("denied")}
        </p>
      )}
    </div>
  );
}
