"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { attachReferral, REFERRAL_KEY } from "@/lib/api/games";
import { useMe } from "@/lib/auth/use-me";
import { Link } from "@/lib/i18n/navigation";

/** Keeps the invitation until the account exists, or links a new account at once. */
export function InviteJoin({ code }: { code: string }) {
  const t = useTranslations("games.invite");
  const me = useMe();
  const [state, setState] = useState<"idle" | "done" | string>("idle");
  const keep = () => {
    try {
      window.localStorage.setItem(REFERRAL_KEY, code);
    } catch {
      // private mode: the link can be opened again after the sign-up
    }
  };
  if (me.data) {
    const link = async () => {
      try {
        await attachReferral(code);
        setState("done");
      } catch (failure) {
        setState(failure instanceof ApiError ? failure.message : t("error"));
      }
    };
    return (
      <div className="flex flex-col gap-3">
        {state === "done" ? (
          <p className="text-feuille font-bold">{t("linked")}</p>
        ) : (
          <Button size="lg" fullWidth onClick={link}>
            {t("link")}
          </Button>
        )}
        {state !== "idle" && state !== "done" && (
          <p role="alert" className="font-bold">
            {state}
          </p>
        )}
        <Link href="/points" className={buttonClasses({ variant: "secondary", fullWidth: true })}>
          {t("seePoints")}
        </Link>
      </div>
    );
  }
  return (
    <Link
      href="/auth?as=client"
      onClick={keep}
      className={buttonClasses({ size: "lg", fullWidth: true })}
    >
      {t("join")}
    </Link>
  );
}
