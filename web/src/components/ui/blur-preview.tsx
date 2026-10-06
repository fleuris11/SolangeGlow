"use client";

import { decode } from "blurhash";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/cn";

/** Blurred preview of a picture (blurhash from the backend), shown while it loads. */
export function BlurPreview({ hash, className }: { hash: string; className?: string }) {
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext("2d");
    if (!element || !context) return;
    try {
      const pixels = decode(hash, 32, 32);
      const image = context.createImageData(32, 32);
      image.data.set(pixels);
      context.putImageData(image, 0, 0);
    } catch {
      // A broken hash simply shows nothing.
    }
  }, [hash]);

  return (
    <canvas
      ref={canvas}
      width={32}
      height={32}
      aria-hidden
      className={cn("block size-full", className)}
    />
  );
}
