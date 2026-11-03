"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { cn } from "@/lib/cn";

type Props = {
  before: string;
  after: string;
  beforeAlt: string;
  afterAlt: string;
  sizes?: string;
  className?: string;
};

const START = 50;

/**
 * Before and after, moved with a finger or the arrow keys: a real slider, so it needs no
 * instructions and works without touching. Only the clip of the top picture changes.
 */
export function BeforeAfterSlider({
  before,
  after,
  beforeAlt,
  afterAlt,
  sizes = "(min-width: 1024px) 50vw, 100vw",
  className,
}: Props) {
  const t = useTranslations("ui.beforeAfter");
  const [position, setPosition] = useState(START);

  return (
    <div
      className={cn("rounded-photo relative aspect-[4/5] overflow-hidden select-none", className)}
    >
      <Image src={after} alt={afterAlt} fill sizes={sizes} className="object-cover" />
      <Image
        src={before}
        alt={beforeAlt}
        fill
        sizes={sizes}
        className="object-cover"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
      />
      <span
        aria-hidden
        className="bg-carte absolute inset-y-0 w-1"
        style={{ left: `${position}%` }}
      />
      <span
        data-ambiance="nuit"
        className="bg-voile-photo text-small absolute top-3 left-3 rounded-full px-3 py-1 font-bold"
      >
        {t("before")}
      </span>
      <span
        data-ambiance="nuit"
        className="bg-voile-photo text-small absolute top-3 right-3 rounded-full px-3 py-1 font-bold"
      >
        {t("after")}
      </span>
      <input
        type="range"
        min={0}
        max={100}
        value={position}
        onChange={(event) => setPosition(Number(event.target.value))}
        aria-label={t("label")}
        className="absolute inset-0 size-full cursor-ew-resize opacity-0"
      />
    </div>
  );
}
