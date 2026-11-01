import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/seo/alternates";
import { SITEMAP_KINDS } from "@/lib/seo/sitemaps";

/** Public pages only: the admin, the API and the personal spaces stay out of search engines. */
export default function robots(): MetadataRoute.Robots {
  const personal = [
    "me",
    "pro",
    "messages",
    "cart",
    "checkout",
    "orders",
    "appointments",
    "cadeau",
    "rdv",
  ];
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin/", "/api/", "/s3/", "/*/embed/", ...personal.map((part) => `/*/${part}`)],
    },
    sitemap: SITEMAP_KINDS.map((kind) => `${SITE_URL}/sitemap/${kind}.xml`),
  };
}
