"use client";

import { Eye, EyeSlash } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Input } from "@/components/ui/input";

type Props = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** "new-password" when the person chooses it, "current-password" to sign in. */
  autoComplete: "new-password" | "current-password";
  hint?: string;
  error?: string;
};

/** Password with a button to see what was typed (easier on a small phone keyboard). */
export function PasswordField({ label, value, onChange, autoComplete, hint, error }: Props) {
  const t = useTranslations("auth.password");
  const [visible, setVisible] = useState(false);
  return (
    <Input
      label={label}
      type={visible ? "text" : "password"}
      autoComplete={autoComplete}
      autoCapitalize="none"
      autoCorrect="off"
      spellCheck={false}
      value={value}
      hint={hint}
      error={error}
      onChange={(event) => onChange(event.target.value)}
      trailing={
        <button
          type="button"
          onClick={() => setVisible((shown) => !shown)}
          aria-pressed={visible}
          aria-label={visible ? t("hide") : t("show")}
          className="text-prune text-small -mr-2 inline-flex min-h-12 shrink-0 items-center gap-1 rounded-full px-2 font-bold"
        >
          {visible ? (
            <EyeSlash aria-hidden size={22} weight="bold" />
          ) : (
            <Eye aria-hidden size={22} weight="bold" />
          )}
          {visible ? t("hideShort") : t("showShort")}
        </button>
      }
    />
  );
}
