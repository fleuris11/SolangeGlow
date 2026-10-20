import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use, type ReactNode } from "react";

import { routing } from "@/lib/i18n/routing";

type Props = { children: ReactNode; params: Promise<{ locale: string }> };

/** Pages shown inside another website (the booking widget): no menu, no header. */
export default function EmbedLayout({ children, params }: Props) {
  const { locale } = use(params);
  setRequestLocale(hasLocale(routing.locales, locale) ? locale : routing.defaultLocale);
  return (
    <main id="main" className="mx-auto w-full max-w-[640px] px-4 py-4">
      {children}
    </main>
  );
}
