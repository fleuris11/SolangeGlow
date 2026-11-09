import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/lib/i18n/request.ts");

const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const s3InternalUrl = process.env.S3_INTERNAL_URL ?? "http://localhost:9000";
const umamiInternalUrl = process.env.UMAMI_INTERNAL_URL ?? "";

const nextConfig: NextConfig = {
  output: "standalone",
  // A second build next to the development server (local Lighthouse runs).
  distDir: process.env.NEXT_DIST_DIR || ".next",
  reactStrictMode: true,
  poweredByHeader: false,
  // Keeps screenshots clean; the e2e container reaches the dev server as "web".
  devIndicators: false,
  allowedDevOrigins: ["web"],
  // Docker Desktop on Windows does not pass file events into the container: the development
  // server polls instead, or it misses new files ("Module not found" on a file that exists).
  ...(process.env.WATCHPACK_POLLING ? { watchOptions: { pollIntervalMs: 1000 } } : {}),
  // Django URLs end with a slash: let them through untouched.
  skipTrailingSlashRedirect: true,
  images: {
    // WebP only: AVIF is lighter but slow to encode, and the first visitor of each size waited
    // seconds for it on a small server (measured: 7 s for the photo at the top of the home).
    formats: ["image/webp"],
    // Our photos are at most 1600 px wide: no larger variants to compute and store.
    deviceSizes: [360, 480, 640, 768, 1024, 1280, 1600],
    // Optimised copies are kept a month: a photo that changes gets a new name.
    minimumCacheTTL: 2_592_000,
  },
  async rewrites() {
    // The browser calls /api/* on the web origin; Next forwards it to Django.
    return [
      { source: "/api/:path*", destination: `${apiInternalUrl}/api/:path*` },
      // Media stored on S3 (MinIO locally): signed links stay valid through this proxy.
      ...(s3InternalUrl ? [{ source: "/s3/:path*", destination: `${s3InternalUrl}/:path*` }] : []),
      // Audience (Umami, no cookies) through the app: no third-party address for the browser.
      ...(umamiInternalUrl
        ? [{ source: "/stats/:path*", destination: `${umamiInternalUrl}/:path*` }]
        : []),
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          {
            key: "Permissions-Policy",
            // Camera and microphone: calls, lives, voice notes; location: nearby pros.
            value: "camera=(self), microphone=(self), geolocation=(self), payment=(), usb=()",
          },
          // Browsers only keep it over HTTPS: harmless in development.
          ...(process.env.NODE_ENV === "production"
            ? [{ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" }]
            : []),
        ],
      },
      {
        // Photos, videos and brand files of public/: kept a day, then checked again.
        source: "/:folder(media|brand)/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=86400, stale-while-revalidate=604800" },
        ],
      },
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
