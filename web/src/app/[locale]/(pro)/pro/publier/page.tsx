import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { LazyCreateFlow } from "@/components/features/social/lazy";
import { withClientMessages } from "@/lib/i18n/client-messages";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("create") };
}

/** Publishing from her professional space: she stays in it, before and after. */
async function ProPublishPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <LazyCreateFlow />;
}

export default withClientMessages(ProPublishPage, "[locale]/(pro)/pro/publier/page.tsx");
