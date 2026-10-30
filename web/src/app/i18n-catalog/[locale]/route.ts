import { hasLocale } from "next-intl";

import { routing } from "@/lib/i18n/routing";

/**
 * The texts of the app in a language, as written in the files: the translations page of
 * the admin searches them by key or by text (module 12). They are public in the app anyway.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) return new Response(null, { status: 404 });
  const messages = (await import(`../../../messages/${locale}.json`)).default;
  return Response.json(messages);
}
