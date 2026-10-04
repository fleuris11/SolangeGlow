import type { Metadata, Viewport } from "next";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { Providers } from "@/components/providers";
import { ServiceWorkerRegistration } from "@/components/pwa/service-worker-registration";
import { brand } from "@/lib/brand";
import { routing } from "@/lib/i18n/routing";
import { preferencesInitScript } from "@/lib/preferences/preferences";

import { atkinson, fraunces } from "../fonts";
import "../globals.css";

type Props = {
  children: ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Omit<Props, "children">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({
    locale: hasLocale(routing.locales, locale) ? locale : routing.defaultLocale,
    namespace: "metadata",
  });

  return {
    title: { default: t("title"), template: `%s | ${t("title")}` },
    description: t("description"),
    applicationName: brand.name,
    appleWebApp: { capable: true, title: brand.name, statusBarStyle: "default" },
    icons: {
      icon: [{ url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" }],
      apple: "/icons/apple-touch-icon.png",
    },
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: brand.backgroundLight },
    { media: "(prefers-color-scheme: dark)", color: brand.backgroundDark },
  ],
};

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);

  return (
    <html
      lang={locale}
      className={`${fraunces.variable} ${atkinson.variable}`}
      data-text-size="normal"
      suppressHydrationWarning
    >
      <head>
        {/* Applies the saved theme and text size before the first paint. */}
        <script dangerouslySetInnerHTML={{ __html: preferencesInitScript }} />
      </head>
      <body className="antialiased">
        <NextIntlClientProvider>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
