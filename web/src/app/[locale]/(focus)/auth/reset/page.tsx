import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { ResetPassword } from "@/components/features/auth/email-link";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ token?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "auth.reset" });
  // The token is in the address: never indexed, never sent to other sites.
  return { title: t("title"), robots: { index: false }, referrer: "no-referrer" };
}

/** The link of « Forgot password » lands here. */
function ResetPage({ params, searchParams }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const { token } = use(searchParams);
  return <ResetPassword token={(token ?? "").slice(0, 300)} />;
}

export default withClientMessages(ResetPage, "[locale]/(focus)/auth/reset/page.tsx");
