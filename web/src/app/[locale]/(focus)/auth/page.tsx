import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { SignInFlow } from "@/components/features/auth/sign-in-flow";
import type { Locale } from "@/lib/i18n/routing";
import { withClientMessages } from "@/lib/i18n/client-messages";

type Props = {
  params: Promise<{ locale: Locale }>;
  searchParams: Promise<{ as?: string; vitrine?: string }>;
};

export async function generateMetadata({ params }: Pick<Props, "params">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "auth" });
  return { title: t("metaTitle"), robots: { index: false } };
}

function AuthPage({ params, searchParams }: Props) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const { as, vitrine } = use(searchParams);
  return (
    <SignInFlow
      as={as === "pro" || as === "client" ? as : undefined}
      pageName={vitrine?.slice(0, 60)}
    />
  );
}

export default withClientMessages(AuthPage, "[locale]/(focus)/auth/page.tsx");
