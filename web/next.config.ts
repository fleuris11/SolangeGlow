import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/lib/i18n/request.ts");

const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  // Keeps screenshots clean; the e2e container reaches the dev server as "web".
  devIndicators: false,
  allowedDevOrigins: ["web"],
  // Django URLs end with a slash: let them through untouched.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    // The browser calls /api/* on the web origin; Next forwards it to Django.
    return [{ source: "/api/:path*", destination: `${apiInternalUrl}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
