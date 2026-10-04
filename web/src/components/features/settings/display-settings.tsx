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
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
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

      <SwitchRow
        icon={<CellSignalLow size={28} weight="duotone" />}
        label={t("dataSaver")}
        description={t("dataSaverText")}
        checked={prefs.dataSaver}
        onChange={(dataSaver) => set({ dataSaver })}
      />
      <SwitchRow
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
