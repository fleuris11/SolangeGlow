"use client";

import { useEffect, useRef } from "react";

import { useMe } from "@/lib/auth/use-me";

import { usePreferences } from "./preferences-provider";
import { fromProfile } from "./profile-sync";

/** Once signed in, the profile's display preferences apply on this device too. */
export function PreferencesSync() {
  const { data: me } = useMe();
  const { update } = usePreferences();
  const appliedFor = useRef<string | null>(null);

  useEffect(() => {
    if (me && appliedFor.current !== me.id) {
      appliedFor.current = me.id;
      update(fromProfile(me), { source: "server" });
    }
    if (!me) appliedFor.current = null;
  }, [me, update]);

  return null;
}
