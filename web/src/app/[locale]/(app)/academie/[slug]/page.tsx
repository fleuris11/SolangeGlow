import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";

import { CourseView } from "@/components/features/academy/course-view";
import { courseOnServer, SITE_URL } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";
import { jsonLdScript } from "@/lib/pros/json-ld";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamic = "force-dynamic";

const SLUG = /^[a-z0-9-]{1,80}$/;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const course = SLUG.test(slug) ? await courseOnServer(slug, locale) : null;
  if (!course) return {};
  return {
    title: course.title,
    description: course.summary || undefined,
    alternates: { canonical: `${SITE_URL}/${locale}/academie/${course.slug}` },
  };
}

export default async function CoursePage({ params }: Props) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  if (!SLUG.test(slug)) notFound();
  const course = await courseOnServer(slug, locale);
  if (!course) notFound();
  // Search engines read the course, its trainer and its price.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Course",
    name: course.title,
    description: course.summary || course.description || course.title,
    inLanguage: course.language,
    url: `${SITE_URL}/${locale}/academie/${course.slug}`,
    provider: { "@type": "Organization", name: course.trainer.name },
    offers: {
      "@type": "Offer",
      category: course.pricing === "free" ? "Free" : "Paid",
      price:
        course.pricing === "paid" ? course.price_minor / (course.currency === "EUR" ? 100 : 1) : 0,
      priceCurrency: course.currency,
    },
  };
  return (
    <>
      <script
        type="application/ld+json"
        // Escaped by jsonLdScript: no "<" can close the script tag.
        dangerouslySetInnerHTML={{ __html: jsonLdScript(jsonLd) }}
      />
      <CourseView course={course} />
    </>
  );
}
