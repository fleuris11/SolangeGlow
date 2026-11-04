"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { logout } from "@/lib/api/accounts";
import { cn } from "@/lib/cn";
import { useRouter } from "@/lib/i18n/navigation";

/** Signs out, always in the same words, then back to the public home with nothing kept. */
export function SignOutButton({ icon, className }: { icon: ReactNode; className?: string }) {
  const t = useTranslations("proSpace");
  const router = useRouter();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      disabled={busy}
      onClick={() => {
        setBusy(true);
        void logout()
          .catch(() => undefined)
          .finally(() => {
            queryClient.clear();
            router.replace("/");
            router.refresh();
          });
      }}
      className={cn(
        "hover:bg-poudre flex min-h-12 w-full items-center gap-3 rounded-lg px-3 font-semibold disabled:opacity-50",
        className,
      )}
    >
      <span aria-hidden className="inline-flex">
        {icon}
      </span>
      {t("signOut")}
    </button>
  );
}
