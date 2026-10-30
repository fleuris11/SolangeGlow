import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";

import { applyOverrides, fetchOverrides } from "./overrides";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;

  const [messages, overrides] = await Promise.all([
    import(`../../messages/${locale}.json`).then((file) => file.default),
    fetchOverrides(locale),
  ]);
  return { locale, messages: applyOverrides(messages, overrides) };
});
