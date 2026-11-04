import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use, type ReactNode } from "react";

import { SiteShell } from "@/components/shell/site-shell";
import { routing } from "@/lib/i18n/routing";

type Props = { children: ReactNode; params: Promise<{ locale: string }> };

/** The site of a pro, the link she shares: no app menu and no other pros around her. */
export default function SiteLayout({ children, params }: Props) {
  const { locale } = use(params);
  setRequestLocale(hasLocale(routing.locales, locale) ? locale : routing.defaultLocale);
  return <SiteShell>{children}</SiteShell>;
}
