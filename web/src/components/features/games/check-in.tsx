"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { attachReferral, checkIn, REFERRAL_KEY } from "@/lib/api/games";

type Props = {
  streak: number;
  done: boolean;
  /** The flame, drawn by the server (no icon code in this island). */
  flame: ReactNode;
};

/** Today's visit, once a day when the home opens: the flame grows, the points are told.
 * It also links a new account to the invitation it came with (referral). */
export function CheckIn({ streak, done, flame }: Props) {
  const t = useTranslations("games.today");
  const [count, setCount] = useState(streak);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let code: string | null = null;
    try {
      code = window.localStorage.getItem(REFERRAL_KEY);
    } catch {
      code = null;
    }
    if (code) {
      attachReferral(code)
        .catch(() => undefined)
        .finally(() => {
          try {
            window.localStorage.removeItem(REFERRAL_KEY);
          } catch {
            // private mode: nothing kept anyway
          }
        });
    }
    if (done) return;
    checkIn()
      .then((result) => {
        setCount(result.streak);
        if (result.gained || result.bonus) {
          setMessage(
            result.bonus
              ? t("bonus", { points: result.gained + result.bonus, days: result.streak })
              : t("gained", { points: result.gained }),
          );
        }
      })
      .catch(() => undefined);
  }, [done, t]);

  return (
    <div className="flex flex-col gap-1">
      <p className="inline-flex items-center gap-2 font-bold">
        {flame}
        <span>{count > 0 ? t("streak", { count }) : t("noStreak")}</span>
      </p>
      <p aria-live="polite" className="text-small text-feuille font-bold">
        {message}
      </p>
    </div>
  );
}
