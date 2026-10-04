import { WarningCircle } from "@phosphor-icons/react/dist/ssr";
import { useId, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/cn";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  /** What happened and what to do. */
  error?: string;
  /** Element shown at the end of the field (e.g. a microphone button). */
  trailing?: ReactNode;
  leading?: ReactNode;
};

export function Input({ label, hint, error, trailing, leading, className, id, ...props }: Props) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const describedBy = [hint && hintId, error && errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label htmlFor={inputId} className="font-bold">
        {label}
      </label>
      <div
        className={cn(
          "rounded-field bg-poudre flex min-h-14 items-center gap-2 border-2 px-4",
          "focus-within:border-hibiscus",
          error ? "border-alerte" : "border-transparent",
        )}
      >
        {leading && (
          <span aria-hidden className="text-prune-doux inline-flex">
            {leading}
          </span>
        )}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className="text-body placeholder:text-prune-doux min-w-0 flex-1 bg-transparent py-3 outline-none"
          {...props}
        />
        {trailing}
      </div>
      {hint && !error && (
        <p id={hintId} className="text-small text-prune-doux">
          {hint}
        </p>
      )}
      {error && (
        <p
          id={errorId}
          role="alert"
          className="text-small text-alerte flex items-start gap-2 font-bold"
        >
          <WarningCircle aria-hidden size={20} weight="fill" className="mt-0.5 shrink-0" />
          {error}
        </p>
      )}
    </div>
  );
}
