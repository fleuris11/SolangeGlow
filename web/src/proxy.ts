import createMiddleware from "next-intl/middleware";
import type { NextRequest } from "next/server";

import { routing } from "./lib/i18n/routing";

const intl = createMiddleware(routing);

// The booking widget of a salon (/fr/embed/<salon>) may be shown inside the websites she
// listed; every other page may only be framed by the site itself (no clickjacking).
const EMBED = /^\/(?:fr|en|sk)\/embed\/([a-z0-9-]{3,40})\/?$/i;
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const known = new Map<string, { domains: string[]; at: number }>();

async function allowedDomains(slug: string): Promise<string[]> {
  const cached = known.get(slug);
  if (cached && Date.now() - cached.at < 60_000) return cached.domains;
  let domains: string[] = [];
  try {
    const response = await fetch(`${API_INTERNAL_URL}/api/v1/widget/${slug}`, {
      headers: { "X-SG-Client": "web" },
      cache: "no-store",
    });
    if (response.ok) {
      const data = (await response.json()) as { allowed_domains?: string[] };
      domains = (data.allowed_domains ?? []).filter((d) => /^[a-z0-9.-]+$/i.test(d));
    }
  } catch {
    // The backend is not reachable: nobody else may frame the page.
  }
  known.set(slug, { domains, at: Date.now() });
  return domains;
}

const VISITOR_COOKIE = "sg_visitor";

export default async function proxy(request: NextRequest) {
  const response = intl(request);
  const embed = request.nextUrl.pathname.match(EMBED);
  const ancestors = embed
    ? (await allowedDomains(embed[1]!.toLowerCase())).map((domain) => `https://${domain}`)
    : [];
  response.headers.set(
    "Content-Security-Policy",
    ["frame-ancestors 'self'", ...ancestors].join(" "),
  );
  // A random visitor id (no personal data): an ad is not shown too often to the same
  // person without an account (module 12).
  if (!request.cookies.get(VISITOR_COOKIE)) {
    response.cookies.set(VISITOR_COOKIE, crypto.randomUUID(), {
      maxAge: 60 * 60 * 24 * 365,
      sameSite: "lax",
      httpOnly: true,
      path: "/",
    });
  }
  return response;
}

export const config = {
  // Every page except the API and media proxies, Next internals and files with an
  // extension (sw.js, icons…). Short links like /aicha get their language (/fr/aicha).
  // The dot is escaped twice: once for the string, once for the pattern.
  matcher: "/((?!api|s3|_next|_vercel|.*\\..*).*)",
};
