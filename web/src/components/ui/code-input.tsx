"use client";

import { useTranslations } from "next-intl";
import { useRef, useState, type ClipboardEvent, type KeyboardEvent } from "react";

import { cn } from "@/lib/cn";

type Props = {
  length?: number;
  label: string;
  error?: string;
  onComplete?: (code: string) => void;
  disabled?: boolean;
  /** Put the cursor in the first box when shown. */
  autoFocus?: boolean;
};

/** One big box per digit: typing moves forward, pasting fills everything. */
export function CodeInput({
  length = 6,
  label,
  error,
  onComplete,
  disabled = false,
  autoFocus = false,
}: Props) {
  const t = useTranslations("code");
  const [digits, setDigits] = useState<string[]>(() => Array(length).fill(""));
  const refs = useRef<Array<HTMLInputElement | null>>([]);

  const commit = (next: string[]) => {
    setDigits(next);
    if (next.every(Boolean)) onComplete?.(next.join(""));
  };

  const fillFrom = (index: number, value: string) => {
    const incoming = value
      .replace(/\D/g, "")
      .slice(0, length - index)
      .split("");
    if (incoming.length === 0) return;
    const next = [...digits];
    incoming.forEach((digit, offset) => {
      next[index + offset] = digit;
    });
    commit(next);
    refs.current[Math.min(index + incoming.length, length - 1)]?.focus();
  };

  const onKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      event.preventDefault();
      const next = [...digits];
      next[index - 1] = "";
      setDigits(next);
      refs.current[index - 1]?.focus();
    } else if (event.key === "ArrowLeft" && index > 0) {
      refs.current[index - 1]?.focus();
    } else if (event.key === "ArrowRight" && index < length - 1) {
      refs.current[index + 1]?.focus();
    }
  };

  const onPaste = (index: number, event: ClipboardEvent<HTMLInputElement>) => {
    event.preventDefault();
    fillFrom(index, event.clipboardData.getData("text"));
  };

  return (
    <fieldset className="flex min-w-0 flex-col gap-3" disabled={disabled}>
      <legend className="mb-3 font-bold">{label}</legend>
      <div className="flex gap-2">
        {digits.map((digit, index) => (
          <input
            key={index}
            ref={(element) => {
              refs.current[index] = element;
            }}
            value={digit}
            inputMode="numeric"
            autoComplete={index === 0 ? "one-time-code" : "off"}
            autoFocus={autoFocus && index === 0}
            pattern="[0-9]*"
            maxLength={length}
            aria-label={t("digit", { position: index + 1, total: length })}
            aria-invalid={error ? true : undefined}
            onChange={(event) => {
              const value = event.target.value;
              if (value === "") {
                const next = [...digits];
                next[index] = "";
                setDigits(next);
              } else {
                // Typing over a filled box gives "old+new": keep the new part. A longer
                // value comes from SMS autofill and fills the following boxes too.
                fillFrom(index, digit && value.startsWith(digit) ? value.slice(1) : value);
              }
            }}
            onKeyDown={(event) => onKeyDown(index, event)}
            onPaste={(event) => onPaste(index, event)}
            onFocus={(event) => event.target.select()}
            className={cn(
              "rounded-field bg-poudre font-display text-headline h-16 w-full max-w-14 min-w-0 border-2 text-center font-bold outline-none",
              "focus:border-hibiscus",
              error ? "border-alerte" : "border-transparent",
            )}
          />
        ))}
      </div>
      {error && (
        <p role="alert" className="text-small text-alerte font-bold">
          {error}
        </p>
      )}
    </fieldset>
  );
}
