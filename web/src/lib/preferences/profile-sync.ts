import type { Me } from "@/lib/api/accounts";

import type { Preferences } from "./preferences";

/** Preference names on the device → field names in the profile. */
export function toProfile(patch: Partial<Preferences>): Partial<Me> {
  const out: Partial<Me> = {};
  if (patch.theme !== undefined) out.theme = patch.theme;
  if (patch.textSize !== undefined) out.text_size = patch.textSize;
  if (patch.dataSaver !== undefined) out.data_saver = patch.dataSaver;
  if (patch.audioMode !== undefined) out.audio_mode = patch.audioMode;
  if (patch.city !== undefined) out.city = patch.city;
  return out;
}

export function fromProfile(me: Me): Partial<Preferences> {
  return {
    theme: me.theme,
    textSize: me.text_size,
    dataSaver: me.data_saver,
    audioMode: me.audio_mode,
    ...(me.city ? { city: me.city } : {}),
  };
}
