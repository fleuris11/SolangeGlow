/**
 * Texts of the app corrected by the team in the admin (module 12), merged into the
 * translation files without redeploying. Read from the API, kept one minute.
 */
type Messages = { [key: string]: string | Messages };

const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const KEEP_SECONDS = 60;

export async function fetchOverrides(locale: string): Promise<Record<string, string>> {
  try {
    const response = await fetch(
      `${API_INTERNAL_URL}/api/v1/i18n/overrides?lang=${encodeURIComponent(locale)}`,
      {
        headers: { "X-SG-Client": "web" },
        next: { revalidate: KEEP_SECONDS },
        signal: AbortSignal.timeout(1500),
      },
    );
    if (!response.ok) return {};
    const data = (await response.json()) as { messages?: Record<string, string> };
    return data.messages ?? {};
  } catch {
    // The backend is not reachable (e.g. during the build): the files are used as they are.
    return {};
  }
}

/** A copy of the messages where each dotted key found (« home.question ») gets its new text. */
export function applyOverrides(messages: Messages, overrides: Record<string, string>): Messages {
  const keys = Object.keys(overrides);
  if (keys.length === 0) return messages;
  const copy = structuredClone(messages);
  for (const key of keys) {
    const parts = key.split(".");
    const last = parts.pop();
    let node: Messages | string | undefined = copy;
    for (const part of parts) {
      node = typeof node === "object" ? node[part] : undefined;
    }
    // Only a text that exists is replaced: a wrong key never breaks a screen.
    if (last && typeof node === "object" && typeof node[last] === "string") {
      node[last] = overrides[key]!;
    }
  }
  return copy;
}
