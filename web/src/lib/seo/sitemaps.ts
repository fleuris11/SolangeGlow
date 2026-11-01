/** The sitemaps of the app, one per kind of public page (listed by robots.txt). */
export const SITEMAP_KINDS = ["main", "pros", "products", "selection", "courses", "pages"] as const;
export type SitemapKind = (typeof SITEMAP_KINDS)[number];
