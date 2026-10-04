"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  applyPreferences,
  DEFAULT_PREFERENCES,
  parsePreferences,
  STORAGE_KEY,
  type Preferences,
} from "./preferences";

type UpdateOptions = {
  /** "server" = value received from the profile: applied here, not sent back. */
  source?: "user" | "server";
};

type PreferencesContextValue = Preferences & {
  update: (patch: Partial<Preferences>, options?: UpdateOptions) => void;
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

function readStored(): Preferences {
  try {
    return parsePreferences(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

type Props = {
  children: ReactNode;
  /** Called when the person changes a preference (e.g. to save it in her profile). */
  onUserChange?: (patch: Partial<Preferences>) => void;
};

export function PreferencesProvider({ children, onUserChange }: Props) {
  const [prefs, setPrefs] = useState<Preferences>(DEFAULT_PREFERENCES);
  const onUserChangeRef = useRef(onUserChange);
  useEffect(() => {
    onUserChangeRef.current = onUserChange;
  }, [onUserChange]);

  // Load after mount: the server cannot know localStorage (the init script already
  // applied the right theme and size to <html> before the first paint).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync from localStorage once
    setPrefs(readStored());
  }, []);

  const update = useCallback((patch: Partial<Preferences>, options: UpdateOptions = {}) => {
    if (options.source !== "server") onUserChangeRef.current?.(patch);
    setPrefs((current) => {
      const next = { ...current, ...patch };
      applyPreferences(next);
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // Private mode or blocked storage: the choice still applies to this visit.
      }
      return next;
    });
  }, []);

  const value = useMemo(() => ({ ...prefs, update }), [prefs, update]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const value = useContext(PreferencesContext);
  if (!value) {
    throw new Error("usePreferences must be used inside <PreferencesProvider>");
  }
  return value;
}
