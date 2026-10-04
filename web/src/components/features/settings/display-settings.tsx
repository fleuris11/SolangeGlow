"use client";

import {
  CellSignalLow,
  Desktop,
  Moon,
  SpeakerHigh,
  Sun,
  TextAa,
  type Icon,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Chip } from "@/components/ui/chip";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/cn";
import type { Preferences, TextSize, Theme } from "@/lib/preferences/preferences";
import { usePreferences } from "@/lib/preferences/preferences-provider";

const THEME_ICONS: Record<Theme, Icon> = { system: Desktop, light: Sun, dark: Moon };
const TEXT_SIZE_SCALE: Record<TextSize, string> = {
  normal: "text-body",
  large: "text-lead",
  xlarge: "text-title",
};

/** Theme, text size, data saver and audio mode. Saved on this device. */
export function DisplaySettings() {
  const t = useTranslations("settings");
  const prefs = usePreferences();
  const toast = useToast();

  const set = (patch: Partial<Preferences>) => {
    prefs.update(patch);
    toast(t("saved"));
  };

  return (
    <section aria-labelledby="display-title" className="flex flex-col gap-6">
      <h2 id="display-title" className="text-title font-bold">
        {t("title")}
      </h2>

      <Group title={t("theme")}>
        {(["system", "light", "dark"] as const).map((theme) => {
          const Icon = THEME_ICONS[theme];
          return (
            <Chip
              key={theme}
              selected={prefs.theme === theme}
              onClick={() => set({ theme })}
              icon={<Icon size={22} weight="duotone" />}
            >
              {t(`themes.${theme}`)}
            </Chip>
          );
        })}
      </Group>

      <Group title={t("textSize")}>
        {(["normal", "large", "xlarge"] as const).map((size) => (
          <Chip
            key={size}
            selected={prefs.textSize === size}
            onClick={() => set({ textSize: size })}
            icon={<TextAa size={22} weight="duotone" />}
          >
            <span className={TEXT_SIZE_SCALE[size]}>{t(`textSizes.${size}`)}</span>
          </Chip>
        ))}
      </Group>

      <Toggle
        icon={<CellSignalLow size={28} weight="duotone" />}
        label={t("dataSaver")}
        description={t("dataSaverText")}
        checked={prefs.dataSaver}
        onChange={(dataSaver) => set({ dataSaver })}
      />
      <Toggle
        icon={<SpeakerHigh size={28} weight="duotone" />}
        label={t("audioMode")}
        description={t("audioModeText")}
        checked={prefs.audioMode}
        onChange={(audioMode) => set({ audioMode })}
      />
    </section>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-3">
      <legend className="mb-3 font-bold">{title}</legend>
      <div className="flex flex-wrap gap-2">{children}</div>
    </fieldset>
  );
}

function Toggle({
  icon,
  label,
  description,
  checked,
  onChange,
}: {
  icon: ReactNode;
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  const t = useTranslations("settings");
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="border-trait bg-carte rounded-card flex w-full items-center gap-4 border p-4 text-left"
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
