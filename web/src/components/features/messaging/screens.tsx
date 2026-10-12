"use client";

import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useEffect, useSyncExternalStore, type ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { hasSession } from "@/lib/api/client";
import { useRouter } from "@/lib/i18n/navigation";

import type { Attachment } from "./composer";

// Downloaded only by signed-in people, after the page is shown (ADR-004).
const ConversationList = dynamic(
  () => import("./conversation-list").then((m) => m.ConversationList),
  { loading: () => <Skeleton className="h-40 rounded-2xl" /> },
);
const Thread = dynamic(() => import("./thread").then((m) => m.Thread), {
  loading: () => <Skeleton className="m-4 h-60 rounded-2xl" />,
});

const subscribeNothing = () => () => {};

function useSignedIn(): boolean | null {
  return useSyncExternalStore(subscribeNothing, hasSession, () => null);
}

/** « Messages »: the list for signed-in people, an invitation for visitors. */
export function MessagesHome({ visitor }: { visitor: ReactNode }) {
  const signedIn = useSignedIn();
  if (signedIn === null) return <Skeleton className="h-40 rounded-2xl" />;
  return signedIn ? <ConversationList /> : <>{visitor}</>;
}

/** What « ?share=post:<id> » or « ?slot=<pro>|<when> » prepares in the composer. */
function useInitialAttachment(share?: string, slot?: string): Attachment | null {
  const t = useTranslations("messages.composer");
  const locale = useLocale();
  if (share?.startsWith("post:")) {
    return { share: { kind: "post", id: share.slice(5) }, label: t("postCard") };
  }
  if (slot) {
    const [pro, when] = slot.split("|");
    const date = when ? new Date(when) : null;
    if (pro && date && !Number.isNaN(date.getTime())) {
      return {
        share: { kind: "slot", pro, starts_at: date.toISOString() },
        label: t("slotCard", {
          when: new Intl.DateTimeFormat(locale, { dateStyle: "full", timeStyle: "short" }).format(
            date,
          ),
        }),
      };
    }
  }
  return null;
}

export function ThreadScreen({
  conversationId,
  share,
  slot,
}: {
  conversationId: string;
  share?: string;
  slot?: string;
}) {
  const signedIn = useSignedIn();
  const router = useRouter();
  const attachment = useInitialAttachment(share, slot);
  useEffect(() => {
    if (signedIn === false) router.replace("/auth");
  }, [signedIn, router]);
  if (!signedIn) return <Skeleton className="m-4 h-60 rounded-2xl" />;
  return <Thread conversationId={conversationId} initialAttachment={attachment} />;
}
