import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { use } from "react";

import { MySection } from "@/components/features/pros/my/my-section";
import { SECTIONS, type Section } from "@/components/features/pros/my/sections";
import type { Locale } from "@/lib/i18n/routing";

type Props = { params: Promise<{ locale: Locale; section: string }> };

const isSection = (value: string): value is Section =>
  (SECTIONS as readonly string[]).includes(value);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, section } = await params;
  if (!isSection(section)) return {};
  const t = await getTranslations({ locale, namespace: "pros.my.sections" });
  return { title: t(section), robots: { index: false } };
}

export default function MySectionPage({ params }: Props) {
  const { locale, section } = use(params);
  setRequestLocale(locale);
  if (!isSection(section)) notFound();
  return <MySection section={section} />;
}
