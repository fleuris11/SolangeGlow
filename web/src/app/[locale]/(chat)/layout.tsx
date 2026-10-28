import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use, type ReactNode } from "react";

import { routing } from "@/lib/i18n/routing";

type Props = { children: ReactNode; params: Promise<{ locale: string }> };

/** Full screen without menu: a conversation, a call, a live room (their own header). */
export default function ChatLayout({ children, params }: Props) {
  const { locale } = use(params);
  setRequestLocale(hasLocale(routing.locales, locale) ? locale : routing.defaultLocale);
  return (
    <main id="main" className="mx-auto w-full max-w-[640px]">
      {children}
    </main>
  );
}
