import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import scopes from "./client-namespaces.json";
import { routing, type Locale } from "./routing";

type Messages = Record<string, unknown>;
export type MessageScope = keyof typeof scopes;

/** Only these message paths ("ns" or "ns.key"), with their nesting kept. */
export function pickMessages(messages: Messages, paths: readonly string[]): Messages {
  const picked: Messages = {};
  for (const path of paths) {
    const parts = path.split(".");
    let source: unknown = messages;
    for (const part of parts) {
      source = source && typeof source === "object" ? (source as Messages)[part] : undefined;
    }
    if (source === undefined) continue;
    let target = picked;
    for (const part of parts.slice(0, -1)) {
      if (typeof target[part] !== "object" || target[part] === null) target[part] = {};
      target = target[part] as Messages;
    }
    target[parts[parts.length - 1]!] = source;
  }
  return picked;
}

/** The translations the browser needs for this scope (scripts/client-messages.mjs). */
export async function scopedMessages(scope: MessageScope, locale?: Locale): Promise<Messages> {
  return pickMessages(
    (await getMessages(locale ? { locale } : undefined)) as Messages,
    scopes[scope],
  );
}

/**
 * A page that sends to the browser only the translations of its own client components, instead
 * of all of them (about 160 KB in every HTML page before). The list is computed from the imports
 * by `npm run messages:scope`, checked in CI.
 */
export function withClientMessages<P extends object>(
  Page: (props: P) => ReactNode | Promise<ReactNode>,
  scope: MessageScope,
) {
  async function ScopedPage(props: P) {
    // The locale from the address, as the page itself does: static pages stay static.
    const params = (props as { params?: Promise<{ locale?: string }> }).params;
    const asked = params ? (await params).locale : undefined;
    const locale = asked && hasLocale(routing.locales, asked) ? asked : undefined;
    if (locale) setRequestLocale(locale);
    return (
      <NextIntlClientProvider messages={await scopedMessages(scope, locale)}>
        <Page {...props} />
      </NextIntlClientProvider>
    );
  }
  ScopedPage.displayName = `Scoped(${Page.name || "Page"})`;
  return ScopedPage;
}
