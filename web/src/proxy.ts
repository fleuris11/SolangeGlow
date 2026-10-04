import createMiddleware from "next-intl/middleware";

import { routing } from "./lib/i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Every page except the API proxy, Next internals and static files (sw.js, icons…).
  matcher: "/((?!api|_next|_vercel|.*\..*).*)",
};
