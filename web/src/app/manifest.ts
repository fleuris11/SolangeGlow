import type { MetadataRoute } from "next";
import { getTranslations } from "next-intl/server";

import { brand } from "@/lib/brand";
import { routing } from "@/lib/i18n/routing";

export default async function manifest(): Promise<MetadataRoute.Manifest> {
  const t = await getTranslations({ locale: routing.defaultLocale, namespace: "manifest" });

  return {
    id: "/",
    name: brand.name,
    short_name: t("shortName"),
    description: t("description"),
    lang: routing.defaultLocale,
    start_url: `/${routing.defaultLocale}`,
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: brand.backgroundLight,
    theme_color: brand.backgroundLight,
    categories: ["beauty", "lifestyle", "shopping"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
