"use client";

import { useTranslations } from "next-intl";
import { useCallback } from "react";

import { useToast } from "@/components/ui/toast";
import { updateMe, type SignIn } from "@/lib/api/accounts";
import { takeReturnPath } from "@/lib/auth/return-path";
import { useSetMe } from "@/lib/auth/use-me";
import { useRouter } from "@/lib/i18n/navigation";
import { usePreferences } from "@/lib/preferences/preferences-provider";
import { toProfile } from "@/lib/preferences/profile-sync";

/** After any way of signing in: keep the visitor's choices, then welcome or back where she was. */
export function useSignedIn(as?: "client" | "pro") {
  const t = useTranslations("auth");
  const router = useRouter();
  const toast = useToast();
  const setMe = useSetMe();
  const prefs = usePreferences();

  return useCallback(
    async ({ created, user, deletion_cancelled: deletionCancelled }: SignIn) => {
      let me = user;
      if (created) {
        // Nothing is lost: choices made as a visitor become the profile's.
        me = await updateMe(toProfile(prefs)).catch(() => user);
      }
      setMe(me);
      if (me.onboarding_required) {
        router.replace(as ? { pathname: "/welcome", query: { as } } : "/welcome");
      } else {
        toast(deletionCancelled ? t("deletionCancelled") : t("welcomeBack"));
        router.replace(takeReturnPath() ?? (me.roles.includes("pro") ? "/pro" : "/"));
      }
    },
    [as, prefs, router, setMe, t, toast],
  );
}
