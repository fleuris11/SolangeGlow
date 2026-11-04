import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use, type ReactNode } from "react";

import { ProShell } from "@/components/shell/pro/pro-shell";
import { routing } from "@/lib/i18n/routing";

type Props = { children: ReactNode; params: Promise<{ locale: string }> };

/** The space of a pro: her own menu, separate from the client's. */
export default function ProLayout({ children, params }: Props) {
  const { locale } = use(params);
  setRequestLocale(hasLocale(routing.locales, locale) ? locale : routing.defaultLocale);
  return <ProShell>{children}</ProShell>;
}
