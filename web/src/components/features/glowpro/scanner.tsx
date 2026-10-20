"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Detector = { detect: (source: HTMLVideoElement) => Promise<{ rawValue: string }[]> };
const FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e", "itf"];

/** The phone's barcode reader when it has one; otherwise a small reader is loaded. */
async function makeDetector(): Promise<Detector> {
  const native = (globalThis as { BarcodeDetector?: new (o: object) => Detector }).BarcodeDetector;
  if (native) return new native({ formats: FORMATS });
  const { BarcodeDetector } = await import("barcode-detector/ponyfill");
  return new BarcodeDetector({ formats: FORMATS as never }) as unknown as Detector;
}

/** Camera view that reads an EAN; the code can also be typed. */
export function Scanner({ onCode }: { onCode: (code: string) => void }) {
  const t = useTranslations("glowpro.stock");
  const video = useRef<HTMLVideoElement>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [typed, setTyped] = useState("");

  useEffect(() => {
    let stream: MediaStream | null = null;
    let timer: number | undefined;
    let stopped = false;
    (async () => {
      try {
        const detector = await makeDetector();
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (stopped || !video.current) return;
        video.current.srcObject = stream;
        await video.current.play();
        const look = async () => {
          if (stopped || !video.current) return;
          try {
            const found = await detector.detect(video.current);
            const code = found.find((f) => /^\d{8,14}$/.test(f.rawValue))?.rawValue;
            if (code) {
              navigator.vibrate?.(60);
              onCode(code);
              return;
            }
          } catch {
            // A frame that could not be read: the next one.
          }
          timer = window.setTimeout(() => void look(), 250);
        };
        void look();
      } catch {
        setProblem(t("noCamera"));
      }
    })();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [onCode, t]);

  return (
    <div className="flex flex-col gap-3">
      {problem ? (
        <p role="alert" className="bg-poudre rounded-2xl p-3 font-bold">
          {problem}
        </p>
      ) : (
        <div className="bg-prune relative overflow-hidden rounded-2xl">
          <video
            ref={video}
            muted
            playsInline
            className="aspect-[4/3] w-full object-cover"
            aria-label={t("camera")}
          />
          <div
            aria-hidden
            className="border-sur-hibiscus absolute inset-x-8 top-1/2 h-0.5 -translate-y-1/2 border-t-2"
          />
        </div>
      )}
      <p className="text-small text-prune-doux">{t("scanHelp")}</p>
      <form
        className="flex items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          const digits = typed.replace(/\D/g, "");
          if (digits.length >= 8) onCode(digits);
        }}
      >
        <Input
          className="flex-1"
          label={t("typeCode")}
          inputMode="numeric"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
        />
        <Button type="submit" variant="secondary">
          {t("search")}
        </Button>
      </form>
    </div>
  );
}
