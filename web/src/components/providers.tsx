"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCallback, useState, type ReactNode } from "react";

import { ToastProvider } from "@/components/ui/toast";
import { meQueryKey, updateMe, type Me } from "@/lib/api/accounts";
import type { Preferences } from "@/lib/preferences/preferences";
import { PreferencesProvider } from "@/lib/preferences/preferences-provider";
import { PreferencesSync } from "@/lib/preferences/preferences-sync";
import { toProfile } from "@/lib/preferences/profile-sync";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
        },
      }),
  );

  // Signed in: a display choice is also saved in the profile, for every device.
  const saveToProfile = useCallback(
    (patch: Partial<Preferences>) => {
      if (!queryClient.getQueryData<Me | null>(meQueryKey)) return;
      updateMe(toProfile(patch))
        .then((me) => queryClient.setQueryData(meQueryKey, me))
        .catch(() => undefined);
    },
    [queryClient],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider onUserChange={saveToProfile}>
        <PreferencesSync />
        <ToastProvider>{children}</ToastProvider>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}
