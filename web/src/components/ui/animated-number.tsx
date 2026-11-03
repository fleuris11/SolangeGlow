"use client";

import { useLocale } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";

type Props = { value: number; className?: string };

/** A number that rolls when it changes (likes, points). It never animates when first shown. */
export function AnimatedNumber({ value, className }: Props) {
  const locale = useLocale();
  const previous = useRef(value);
  const [direction, setDirection] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (value !== previous.current) {
      setDirection(value > previous.current ? "up" : "down");
      previous.current = value;
    }
  }, [value]);

  return (
    <span className={cn("inline-block overflow-hidden tabular-nums", className)}>
      <span key={value} className={cn("inline-block", direction && `sg-roll-${direction}`)}>
        {new Intl.NumberFormat(locale).format(value)}
      </span>
    </span>
  );
}
