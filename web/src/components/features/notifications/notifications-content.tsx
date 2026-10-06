"use client";

import { BellRinging, SignIn } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/lib/auth/use-me";
import { Link } from "@/lib/i18n/navigation";

import { NotificationList } from "./notification-list";
import { NotificationSettings } from "./notification-settings";

export function NotificationsContent() {
  const t = useTranslations("notifications");
  const { data: me, isPending } = useMe();

  if (isPending) return <Skeleton className="h-32" />;

  if (!me) {
    return (
      <EmptyState
        icon={<BellRinging size={48} weight="duotone" />}
        title={t("visitorTitle")}
        description={t("visitorText")}
        action={
          <Button asChild size="lg">
            <Link href="/auth">
              <SignIn aria-hidden size={24} weight="bold" />
              {t("signIn")}
            </Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-10">
      <NotificationList />
      <NotificationSettings me={me} />
    </div>
  );
}
