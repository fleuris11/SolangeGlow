import createMiddleware from "next-intl/middleware";

import { routing } from "./lib/i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Every page except the API and media proxies, Next internals and files with an
  // extension (sw.js, icons…). Short links like /aicha get their language (/fr/aicha).
  // The dot is escaped twice: once for the string, once for the pattern.
  matcher: "/((?!api|s3|_next|_vercel|.*\\..*).*)",
};
