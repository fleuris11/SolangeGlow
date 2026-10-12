import { Camera } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Link } from "@/lib/i18n/navigation";
import { LazyCreateFlow } from "@/components/features/social/lazy";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "nav" });
  return { title: t("create") };
}

export default async function CreatePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "create" });
  const signedIn = (await cookies()).get("sg_signed_in")?.value === "1";

  if (signedIn) return <LazyCreateFlow />;
  return (
    <>
      <h1 className="sr-only">{t("title")}</h1>
      <EmptyState
        icon={<Camera size={48} weight="duotone" />}
        title={t("emptyTitle")}
        description={t("emptyText")}
        action={
          <Button asChild size="lg">
            <Link href="/auth">{t("cta")}</Link>
          </Button>
        }
      />
    </>
  );
}
