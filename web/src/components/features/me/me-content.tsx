"use client";

import { SignIn, UserCirclePlus } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import { Button } from "@/components/ui/button";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/lib/auth/use-me";
import { Link } from "@/lib/i18n/navigation";

// Signed-in screens (forms, validation) are downloaded only for signed-in people:
// a visitor's first load stays within the JavaScript budget (ADR-004).
const ProfileForm = dynamic(() => import("./profile-form").then((m) => m.ProfileForm), {
  loading: () => <Skeleton className="h-64" />,
});
const AccountSettings = dynamic(() => import("./account-settings").then((m) => m.AccountSettings));
const GuestCard = dynamic(() => import("./guest-card").then((m) => m.GuestCard));
const DisplaySettings = dynamic(() =>
  import("@/components/features/settings/display-settings").then((m) => m.DisplaySettings),
);

/** "Me": the profile once signed in; otherwise sign-in, guest booking and display settings. */
export function MeContent() {
  const t = useTranslations("me");
  const { data: me, isPending } = useMe();

  if (isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4">
        <Skeleton className="petal size-32 rounded-none" />
        <Skeleton className="h-6 w-2/3 rounded-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-10">
      {me ? (
        <ProfileForm me={me} />
      ) : (
        <>
          <section
            aria-labelledby="signin-title"
            className="bg-poudre rounded-card flex flex-col items-start gap-3 p-5"
          >
            <UserCirclePlus aria-hidden size={40} weight="duotone" className="text-hibiscus" />
            <h2 id="signin-title" className="text-title font-bold">
              {t("guestTitle")}
            </h2>
            <p className="text-prune-doux">{t("guestText")}</p>
            <Button asChild size="lg">
              <Link href="/auth">
                <SignIn aria-hidden size={24} weight="bold" />
                {t("cta")}
              </Link>
            </Button>
          </section>
          <GuestCard />
        </>
      )}

      <DisplaySettings />

      <section aria-labelledby="language-title" className="flex flex-col gap-3">
        <h2 id="language-title" className="text-title font-bold">
          {t("language")}
        </h2>
        <LocaleSwitcher />
      </section>

      {me && <AccountSettings me={me} />}
    </div>
  );
}
