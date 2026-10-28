"use client";

import { ArrowLeft, ShieldCheck, Storefront, UserPlus } from "@phosphor-icons/react";
import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  acceptRequest,
  declineRequest,
  deleteMessage,
  getConversation,
  getMessages,
  markRead,
  reportMessage,
  sendMessage,
  type Conversation,
  type Message,
  type MessageInput,
  type MessagePage,
} from "@/lib/api/messaging";
import { messagingUnreadKey } from "@/lib/api/messaging-unread";
import { useMe } from "@/lib/auth/use-me";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { isConnected, send as sendEvent, subscribe } from "@/lib/messaging/bus";
import * as outbox from "@/lib/messaging/outbox";
import { mediaSrc } from "@/lib/media";

import { ActiveCallBanner, CallButtons } from "../calls/call-bar";
import { Composer, type Attachment } from "./composer";
import { MessageBubble, type Delivery } from "./message-bubble";

type Pages = InfiniteData<MessagePage, string | undefined>;

function dayKey(iso: string): string {
  return new Date(iso).toDateString();
}

function useDayLabel() {
  const t = useTranslations("messages.thread");
  const locale = useLocale();
  return (iso: string) => {
    const date = new Date(iso);
    const today = new Date();
    const yesterday = new Date(today.getTime() - 86_400_000);
    if (date.toDateString() === today.toDateString()) return t("today");
    if (date.toDateString() === yesterday.toDateString()) return t("yesterday");
    return new Intl.DateTimeFormat(locale, { dateStyle: "full" }).format(date);
  };
}

function deliveryOf(message: Message, conversation: Conversation | undefined): Delivery {
  const at = message.created_at;
  const { read_up_to: read, delivered_up_to: delivered } = conversation?.receipts ?? {};
  if (read && read >= at) return "read";
  if (delivered && delivered >= at) return "received";
  return "sent";
}

/** Adds or replaces a message in the newest page of the cache. */
function upsert(data: Pages | undefined, message: Message): Pages | undefined {
  if (!data) return data;
  const exists = data.pages.some((page) => page.results.some((m) => m.id === message.id));
  if (exists) {
    return {
      ...data,
      pages: data.pages.map((page) => ({
        ...page,
        results: page.results.map((m) => (m.id === message.id ? message : m)),
      })),
    };
  }
  const [newest, ...rest] = data.pages;
  if (!newest) return data;
  return { ...data, pages: [{ ...newest, results: [...newest.results, message] }, ...rest] };
}

/** One conversation: messages (live), receipts, typing, and the composer. */
export function Thread({
  conversationId,
  initialAttachment = null,
}: {
  conversationId: string;
  initialAttachment?: Attachment | null;
}) {
  const t = useTranslations("messages.thread");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const dayLabel = useDayLabel();
  const { data: me } = useMe();
  const [attachment, setAttachment] = useState<Attachment | null>(initialAttachment);
  const [typingUntil, setTypingUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const bottom = useRef<HTMLDivElement>(null);
  const conversationKey = useMemo(() => ["conversation", conversationId], [conversationId]);
  const messagesKey = useMemo(() => ["messages", conversationId], [conversationId]);

  const conversation = useQuery({
    queryKey: conversationKey,
    queryFn: () => getConversation(conversationId),
  });
  const messages = useInfiniteQuery({
    queryKey: messagesKey,
    queryFn: ({ pageParam }) => getMessages(conversationId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next ?? undefined,
  });
  const pending = useSyncExternalStore(
    outbox.onChange,
    () => JSON.stringify(outbox.pendingFor(conversationId)),
    () => "[]",
  );
  const waiting = useMemo(() => JSON.parse(pending) as outbox.Pending[], [pending]);

  const flush = () =>
    outbox.flush(
      async (item) => {
        const sent = await sendMessage(item.conversationId, {
          ...item.body,
          client_id: item.clientId,
        });
        queryClient.setQueryData<Pages>(messagesKey, (data) => upsert(data, sent));
        // Receipts and the pay-in-the-app warning may have changed.
        void queryClient.invalidateQueries({ queryKey: conversationKey });
      },
      (error) => {
        const refused =
          error instanceof ApiError &&
          error.status >= 400 &&
          error.status < 500 &&
          error.status !== 429;
        if (refused) toast(error.message, "warning");
        return refused;
      },
    );

  const read = () => {
    if (document.visibilityState !== "visible") return;
    if (!sendEvent({ type: "read", conversation: conversationId })) {
      void markRead(conversationId).catch(() => undefined);
    }
    void queryClient.invalidateQueries({ queryKey: messagingUnreadKey });
  };

  // Live events, read receipts, viewing state, offline queue and polling without socket.
  useEffect(() => {
    // Full-screen conversation, no menu: start the live connection here.
    void import("@/lib/messaging/socket").then(({ startSocket }) => startSocket());
    sendEvent({ type: "viewing", conversation: conversationId });
    read();
    void flush();
    const unsubscribe = subscribe((event) => {
      if (event.type === "message" && event.message.conversation_id === conversationId) {
        queryClient.setQueryData<Pages>(messagesKey, (data) => upsert(data, event.message));
        if (event.message.client_id) outbox.remove(event.message.client_id);
        if (event.message.sender_id !== me?.id) {
          setTypingUntil(0);
          read();
        }
        void queryClient.invalidateQueries({ queryKey: conversationKey });
      } else if (event.type === "receipt" && event.conversation === conversationId) {
        void queryClient.invalidateQueries({ queryKey: conversationKey });
      } else if (event.type === "typing" && event.conversation === conversationId) {
        setTypingUntil(Date.now() + 4000);
      } else if (event.type === "presence") {
        queryClient.setQueryData<Conversation>(conversationKey, (data) =>
          data
            ? {
                ...data,
                people: data.people.map((p) =>
                  p.id === event.user
                    ? { ...p, online: event.online, last_seen: event.last_seen }
                    : p,
                ),
              }
            : data,
        );
      } else if (event.type === "conversation" && event.conversation === conversationId) {
        void queryClient.invalidateQueries({ queryKey: conversationKey });
      } else if (event.type === "connected") {
        void flush();
        void queryClient.invalidateQueries({ queryKey: messagesKey });
      }
    });
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        sendEvent({ type: "viewing", conversation: conversationId });
        read();
      }
    };
    const onOnline = () => void flush();
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("online", onOnline);
    // Without the live connection (blocked network, proxy), look for news every 10 s.
    const poll = window.setInterval(() => {
      setNow(Date.now());
      if (!isConnected()) {
        void queryClient.invalidateQueries({ queryKey: messagesKey });
        void queryClient.invalidateQueries({ queryKey: conversationKey });
        void flush();
      }
    }, 10_000);
    return () => {
      unsubscribe();
      sendEvent({ type: "viewing", conversation: null });
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("online", onOnline);
      window.clearInterval(poll);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, me?.id]);

  const all = useMemo(
    () => [...(messages.data?.pages ?? [])].reverse().flatMap((page) => page.results),
    [messages.data],
  );
  const shown = all.filter((m) => !waiting.some((p) => p.clientId === m.client_id));

  // Follow the conversation: keep the newest message in view.
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: "end" });
  }, [shown.length, waiting.length]);

  // Typing indicator vanishes after a few seconds.
  useEffect(() => {
    if (typingUntil <= Date.now()) return;
    const timer = window.setTimeout(() => setNow(Date.now()), typingUntil - Date.now());
    return () => window.clearTimeout(timer);
  }, [typingUntil]);

  const send = (body: MessageInput) => {
    outbox.add({
      clientId: outbox.newClientId(),
      conversationId,
      body,
      createdAt: new Date().toISOString(),
    });
    void flush();
  };

  const retry = (clientId: string) => {
    const item = outbox.pendingFor(conversationId).find((p) => p.clientId === clientId);
    if (item) {
      outbox.add({ ...item, failed: false });
      void flush();
    }
  };

  const data = conversation.data;
  const person = data?.people[0];
  const myLast = [...shown].reverse().find((m) => m.sender_id === me?.id);
  const isTyping = typingUntil > now;
  const subtitle = isTyping
    ? t("typing", { name: person?.name ?? "" })
    : person?.online
      ? t("online")
      : person?.last_seen
        ? t("lastSeen", {
            time: new Intl.DateTimeFormat(locale, {
              dateStyle: "short",
              timeStyle: "short",
            }).format(new Date(person.last_seen)),
          })
        : "";

  if (conversation.isError) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <p role="alert" className="font-bold">
          {conversation.error instanceof ApiError ? conversation.error.message : t("error")}
        </p>
        <Link href="/messages" className={buttonClasses({ variant: "secondary" })}>
          {t("back")}
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="bg-carte border-trait sticky top-0 z-10 flex items-center gap-1 border-b px-2 py-2 sm:gap-3">
        <Link
          href="/messages"
          aria-label={t("back")}
          className="hover:bg-poudre inline-flex size-12 shrink-0 items-center justify-center rounded-full"
        >
          <ArrowLeft aria-hidden size={26} weight="bold" />
        </Link>
        {data ? (
          <>
            <span className="relative shrink-0">
              <Avatar name={data.title} src={mediaSrc(person?.photo, "thumb")} size="sm" />
              {person?.online && (
                <span
                  aria-hidden
                  className="bg-feuille border-carte absolute -right-0.5 -bottom-0.5 size-3.5 rounded-full border-2"
                />
              )}
            </span>
            <div className="ml-2 flex min-w-0 flex-1 flex-col">
              <h1 className="truncate font-bold">{data.title}</h1>
              <p className="text-mention text-prune-doux truncate" aria-live="polite">
                {subtitle}
              </p>
            </div>
            <CallButtons conversationId={conversationId} />
            {person?.pro_slug && (
              <Link
                href={`/${person.pro_slug}`}
                className={buttonClasses({
                  variant: "quiet",
                  className: "w-12 shrink-0 px-0 sm:w-auto sm:px-5",
                })}
              >
                <Storefront aria-hidden size={22} weight="bold" />
                <span className="sr-only sm:not-sr-only">{t("showcase")}</span>
              </Link>
            )}
          </>
        ) : (
          <Skeleton className="h-10 flex-1" />
        )}
      </header>

      <ActiveCallBanner conversationId={conversationId} />

      {data?.payment_warning && (
        <div className="bg-poudre mx-4 mt-3 flex gap-3 rounded-2xl p-4" role="note">
          <ShieldCheck aria-hidden size={28} weight="fill" className="text-hibiscus shrink-0" />
          <div className="flex flex-col gap-1">
            <p className="font-bold">{t("payInApp")}</p>
            <p className="text-small">{t("payInAppText")}</p>
          </div>
        </div>
      )}

      <div className="flex flex-1 flex-col gap-3 px-4 py-4">
        {messages.hasNextPage && (
          <Button
            variant="quiet"
            className="self-center"
            disabled={messages.isFetchingNextPage}
            onClick={() => void messages.fetchNextPage()}
          >
            {t("older")}
          </Button>
        )}
        {messages.isPending && <Skeleton className="rounded-card h-40" />}
        {messages.isSuccess && shown.length === 0 && waiting.length === 0 && (
          <p className="text-prune-doux my-8 text-center">
            {t("empty", { name: data?.title ?? "" })}
          </p>
        )}
        <ol className="flex flex-col gap-3" aria-label={t("list")}>
          {shown.map((message, index) => {
            const previous = shown[index - 1];
            const newDay = !previous || dayKey(previous.created_at) !== dayKey(message.created_at);
            const mine = message.sender_id === me?.id;
            return (
              <li key={message.id} className="flex flex-col gap-3">
                {newDay && (
                  <p className="text-mention text-prune-doux text-center font-bold">
                    {dayLabel(message.created_at)}
                  </p>
                )}
                <MessageBubble
                  message={message}
                  mine={mine}
                  delivery={message.id === myLast?.id ? deliveryOf(message, data) : undefined}
                  onDelete={
                    mine
                      ? () =>
                          void deleteMessage(message.id)
                            .then(() => queryClient.invalidateQueries({ queryKey: messagesKey }))
                            .catch((error: unknown) =>
                              toast(
                                error instanceof ApiError ? error.message : t("error"),
                                "warning",
                              ),
                            )
                      : undefined
                  }
                  onReport={
                    mine
                      ? undefined
                      : () =>
                          void reportMessage(message.id, "harassment")
                            .then(() => toast(t("reported"), "success"))
                            .catch((error: unknown) =>
                              toast(
                                error instanceof ApiError ? error.message : t("error"),
                                "warning",
                              ),
                            )
                  }
                />
              </li>
            );
          })}
          {waiting.map((item) => (
            <li key={item.clientId}>
              <MessageBubble
                mine
                message={{
                  id: item.clientId,
                  conversation_id: conversationId,
                  sender_id: me?.id ?? null,
                  kind: item.body.share ? "share" : item.body.media_id ? "photo" : "text",
                  text: item.body.text ?? "",
                  media: null,
                  share: null,
                  call: null,
                  client_id: item.clientId,
                  fraud_labels: [],
                  is_automatic: false,
                  state: "visible",
                  created_at: item.createdAt,
                }}
                delivery={item.failed ? "failed" : "waiting"}
                onRetry={() => retry(item.clientId)}
              />
            </li>
          ))}
        </ol>
        <div ref={bottom} />
      </div>

      <footer className="bg-lait border-trait pb-safe sticky bottom-0 border-t px-4 pt-3 pb-3">
        {data?.status === "requested" ? (
          <div className="flex flex-col gap-3">
            <p className="font-bold">{t("requestFrom", { name: data.title })}</p>
            <p className="text-small text-prune-doux">{t("requestHelp")}</p>
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant="secondary"
                onClick={() =>
                  void declineRequest(conversationId).then(() => router.push("/messages"))
                }
              >
                {t("decline")}
              </Button>
              <Button
                onClick={() =>
                  void acceptRequest(conversationId).then((value) =>
                    queryClient.setQueryData(conversationKey, value),
                  )
                }
              >
                <UserPlus aria-hidden size={22} weight="bold" />
                {t("accept")}
              </Button>
            </div>
          </div>
        ) : data?.is_closed ? (
          <p className="text-prune-doux text-center">{t("closed")}</p>
        ) : (
          <>
            {data?.waiting_for_answer && (
              <p className="text-small text-prune-doux mb-2">{t("waitingAnswer")}</p>
            )}
            <Composer
              conversationId={conversationId}
              isPro={!!me?.is_pro}
              attachment={attachment}
              onAttachmentChange={setAttachment}
              onSend={send}
            />
          </>
        )}
      </footer>
    </div>
  );
}
