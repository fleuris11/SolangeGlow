"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** A setting that is on or off: icon, name, explanation, and an explicit "On / Off". */
export function SwitchRow({
  icon,
  label,
  description,
  checked,
  onChange,
  disabled = false,
}: {
  icon: ReactNode;
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  const t = useTranslations("settings");
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      disabled={disabled}
      className="border-trait bg-carte rounded-card flex w-full items-center gap-4 border p-4 text-left disabled:opacity-60"
    >
      <span aria-hidden className="text-hibiscus shrink-0">
        {icon}
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="font-bold">{label}</span>
        <span className="text-small text-prune-doux">{description}</span>
      </span>
      <span className="flex shrink-0 flex-col items-center gap-1">
        <span
          aria-hidden
          className={cn(
            "relative inline-flex h-8 w-14 rounded-full transition-colors duration-150",
            checked ? "bg-feuille" : "bg-trait",
          )}
        >
          <span
            className={cn(
              "bg-carte absolute top-1 size-6 rounded-full transition-transform duration-150",
              checked ? "translate-x-7" : "translate-x-1",
            )}
          />
        </span>
        <span aria-hidden className="text-mention font-bold">
          {checked ? t("on") : t("off")}
        </span>
      </span>
    </button>
  );
}
