/**
 * Display preferences of the visitor. Stored in localStorage; once signed in they are
 * also saved in the profile (User fields theme, text_size, data_saver, audio_mode).
 */
export const THEMES = ["system", "light", "dark"] as const;
export const TEXT_SIZES = ["normal", "large", "xlarge"] as const;

export type Theme = (typeof THEMES)[number];
export type TextSize = (typeof TEXT_SIZES)[number];

export type Preferences = {
  theme: Theme;
  textSize: TextSize;
  dataSaver: boolean;
  audioMode: boolean;
  /** City used to suggest nearby pros. */
  city: string;
};

export const STORAGE_KEY = "sg.preferences";

export const DEFAULT_PREFERENCES: Preferences = {
  theme: "system",
  textSize: "normal",
  dataSaver: false,
  audioMode: false,
  city: "Cotonou",
};

export function parsePreferences(raw: string | null): Preferences {
  if (!raw) return DEFAULT_PREFERENCES;
  try {
    const value = JSON.parse(raw) as Partial<Preferences>;
    return {
      theme: THEMES.includes(value.theme as Theme) ? (value.theme as Theme) : "system",
      textSize: TEXT_SIZES.includes(value.textSize as TextSize)
        ? (value.textSize as TextSize)
        : "normal",
      dataSaver: value.dataSaver === true,
      audioMode: value.audioMode === true,
      city:
        typeof value.city === "string" && value.city.trim()
          ? value.city.slice(0, 80)
          : DEFAULT_PREFERENCES.city,
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

/** Reflects the preferences on <html> so CSS can react (theme, text size, data saver). */
export function applyPreferences(prefs: Preferences, root: HTMLElement = document.documentElement) {
  if (prefs.theme === "system") {
    delete root.dataset.theme;
  } else {
    root.dataset.theme = prefs.theme;
  }
  root.dataset.textSize = prefs.textSize;
  root.dataset.dataSaver = String(prefs.dataSaver);
}

/**
 * Runs in <head> before the first paint, so there is no flash of the wrong theme or size.
 * Kept tiny and dependency-free on purpose.
 */
export const preferencesInitScript = `(function(){try{var p=JSON.parse(localStorage.getItem("${STORAGE_KEY}")||"{}"),r=document.documentElement;if(p.theme==="light"||p.theme==="dark")r.dataset.theme=p.theme;r.dataset.textSize=["large","xlarge"].indexOf(p.textSize)>-1?p.textSize:"normal";r.dataset.dataSaver=p.dataSaver===true?"true":"false"}catch(e){}})();`;
