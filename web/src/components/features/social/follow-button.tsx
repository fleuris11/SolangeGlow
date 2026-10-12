"use client";

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { hasSession } from "@/lib/api/client";
import { follow } from "@/lib/api/feed";
import { useRouter } from "@/lib/i18n/navigation";

type Props = {
  userId: string;
  followed: boolean;
  count: number;
  /** Drawn by the server page. */
  icons: { follow: ReactNode; following: ReactNode };
};

/** « Follow » a pro: her posts come first in the feed. */
export function FollowButton({ userId, followed, count, icons }: Props) {
  const t = useTranslations("social.follow");
  const router = useRouter();
  const [on, setOn] = useState(followed);
  const [total, setTotal] = useState(count);

  const toggle = async () => {
    if (!hasSession()) {
      router.push("/auth");
      return;
    }
    const next = !on;
    setOn(next);
    setTotal((value) => value + (next ? 1 : -1));
    try {
      await follow(userId, next);
    } catch {
      setOn(!next);
      setTotal((value) => value + (next ? -1 : 1));
    }
  };

  return (
    <div className="flex items-center gap-3">
      <Button variant={on ? "quiet" : "secondary"} aria-pressed={on} onClick={() => void toggle()}>
        {on ? icons.following : icons.follow}
        {on ? t("following") : t("follow")}
      </Button>
      <span className="text-small text-prune-doux">{t("followers", { count: total })}</span>
    </div>
  );
}
