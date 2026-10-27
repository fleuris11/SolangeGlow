import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { CertificateCheckView } from "@/components/features/academy/certificate-check";
import { certificateOnServer } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; code: string }> };

// Rendered on the server: a check made by scanning the QR code needs no script.
export const dynamic = "force-dynamic";

const CODE = /^[A-Za-z0-9-]{4,20}$/;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "academy.titles" });
  return { title: t("certificate"), robots: { index: false, follow: false } };
}

export default async function Page({ params }: Props) {
  const { locale, code } = await params;
  setRequestLocale(locale);
  const certificate = CODE.test(code) ? await certificateOnServer(code, locale) : null;
  return <CertificateCheckView code={code} certificate={certificate} />;
}
