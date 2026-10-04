import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";

import { ToastProvider } from "@/components/ui/toast";
import type { Locale } from "@/lib/i18n/routing";
import { PreferencesProvider } from "@/lib/preferences/preferences-provider";
import messages from "@/messages/fr.json";

/** Renders a component with the providers of the app (French messages, fresh state). */
export function renderWithProviders(ui: ReactElement, { locale = "fr" }: { locale?: Locale } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <NextIntlClientProvider locale={locale} messages={messages} timeZone="Europe/Paris">
      <QueryClientProvider client={queryClient}>
        <PreferencesProvider>
          <ToastProvider>{ui}</ToastProvider>
        </PreferencesProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}
