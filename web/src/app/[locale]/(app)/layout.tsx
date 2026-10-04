import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use, type ReactNode } from "react";

import { AppShell } from "@/components/shell/app-shell";
import { routing } from "@/lib/i18n/routing";

type Props = { children: ReactNode; params: Promise<{ locale: string }> };

export default function AppLayout({ children, params }: Props) {
  const { locale } = use(params);
  // Lets the shell be rendered statically (no need to read the request headers).
  setRequestLocale(hasLocale(routing.locales, locale) ? locale : routing.defaultLocale);
  return <AppShell>{children}</AppShell>;
}
