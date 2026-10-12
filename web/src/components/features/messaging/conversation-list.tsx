"use client";

import { Image as ImageIcon, Microphone, ShieldWarning, Tag } from "@phosphor-icons/react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getConversations, type Conversation } from "@/lib/api/messaging";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { subscribe } from "@/lib/messaging/bus";
import { useMessagingUnread } from "@/lib/messaging/use-messaging-unread";
import { mediaSrc } from "@/lib/media";

function Preview({ conversation }: { conversation: Conversation }) {
  const t = useTranslations("messages.list");
  const last = conversation.last_message;
  if (!last) return <span>{t("noMessage")}</span>;
  if (last.state === "deleted" || last.state === "removed") return <span>{t("deleted")}</span>;
  const icon =
    last.kind === "photo" ? (
      <ImageIcon aria-hidden size={16} weight="bold" />
    ) : last.kind === "voice" ? (
      <Microphone aria-hidden size={16} weight="bold" />
    ) : last.kind === "share" ? (
      <Tag aria-hidden size={16} weight="bold" />
    ) : null;
  const words =
    last.text ||
    (last.kind === "photo"
      ? t("photo")
      : last.kind === "voice"
        ? t("voice")
        : last.kind === "share"
          ? (last.share?.title ?? t("card"))
          : "");
  return (
    <span className="flex min-w-0 items-center gap-1">
      {icon}
      <span className="truncate">{words}</span>
    </span>
  );
}

function Row({ conversation }: { conversation: Conversation }) {
  const t = useTranslations("messages.list");
  const locale = useLocale();
  const person = conversation.people[0];
  const unread = conversation.unread > 0;
  const when = conversation.last_message_at
    ? new Intl.DateTimeFormat(locale, {
        ...(new Date(conversation.last_message_at).toDateString() === new Date().toDateString()
          ? { timeStyle: "short" }
          : { day: "numeric", month: "short" }),
      }).format(new Date(conversation.last_message_at))
    : "";
  return (
    <Link
      href={`/messages/${conversation.id}`}
      className="hover:bg-poudre flex min-h-20 items-center gap-3 rounded-2xl px-2 py-3"
    >
      <span className="relative shrink-0">
        <Avatar name={conversation.title} src={mediaSrc(person?.photo, "thumb")} size="md" />
        {person?.online && (
          <span
            aria-hidden
            className="bg-feuille border-carte absolute right-0 bottom-0 size-4 rounded-full border-2"
          />
        )}
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="flex items-center justify-between gap-2">
          <span className={cn("truncate", unread ? "font-black" : "font-bold")}>
            {conversation.title}
          </span>
          <span className="text-mention text-prune-doux shrink-0">{when}</span>
        </span>
        <span
          className={cn(
            "text-small flex items-center gap-2",
            unread ? "text-prune font-bold" : "text-prune-doux",
          )}
        >
          <Preview conversation={conversation} />
          {conversation.payment_warning && (
            <ShieldWarning
              aria-label={t("warning")}
              size={18}
              weight="fill"
              className="text-alerte shrink-0"
            />
          )}
          {unread && (
            <span className="bg-hibiscus text-sur-hibiscus text-mention ml-auto inline-flex min-w-6 shrink-0 items-center justify-center rounded-full px-1.5 leading-6">
              <span className="sr-only">{t("unread", { count: conversation.unread })}</span>
              <span aria-hidden>{conversation.unread}</span>
            </span>
          )}
        </span>
      </span>
    </Link>
  );
}

/** Her conversations, newest first, and the requests of people she does not know yet. */
export function ConversationList() {
  const t = useTranslations("messages.list");
  const queryClient = useQueryClient();
  const [box, setBox] = useState<"inbox" | "requests">(() =>
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("box") === "requests"
      ? "requests"
      : "inbox",
  );
  const { requests } = useMessagingUnread();
  const query = useInfiniteQuery({
    queryKey: ["conversations", box],
    queryFn: ({ pageParam }) => getConversations(box, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next ?? undefined,
  });

  // A new message or a receipt somewhere: refresh the list.
  useEffect(
    () =>
      subscribe((event) => {
        if (
          event.type === "message" ||
          event.type === "conversation" ||
          event.type === "connected"
        ) {
          void queryClient.invalidateQueries({ queryKey: ["conversations"] });
        }
      }),
    [queryClient],
  );

  const rows = query.data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div
        role="tablist"
        aria-label={t("boxes")}
        className="bg-poudre grid grid-cols-2 rounded-full p-1"
      >
        {(["inbox", "requests"] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={box === key}
            onClick={() => setBox(key)}
            className={cn(
              "min-h-12 rounded-full px-3 font-bold",
              box === key ? "bg-carte text-prune shadow-sm" : "text-prune-doux",
            )}
          >
            {key === "inbox" ? t("inbox") : t("requests", { count: requests })}
          </button>
        ))}
      </div>
      {box === "requests" && <p className="text-small text-prune-doux">{t("requestsHelp")}</p>}
      {query.isPending ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-20 rounded-2xl" />
          <Skeleton className="h-20 rounded-2xl" />
        </div>
      ) : query.isError ? (
        <p role="alert" className="font-bold">
          {t("error")}
        </p>
      ) : rows.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-lead font-bold">
            {box === "inbox" ? t("emptyTitle") : t("noRequests")}
          </p>
          {box === "inbox" && <p className="text-prune-doux">{t("emptyText")}</p>}
        </div>
      ) : (
        <ul className="flex flex-col">
          {rows.map((conversation) => (
            <li key={conversation.id}>
              <Row conversation={conversation} />
            </li>
          ))}
        </ul>
      )}
      {query.hasNextPage && (
        <Button
          variant="secondary"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {t("more")}
        </Button>
      )}
    </div>
  );
}
