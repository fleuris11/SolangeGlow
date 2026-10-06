"use client";

import { BellSimpleSlash, Checks } from "@phosphor-icons/react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  listNotifications,
  markRead,
  notificationsQueryKey,
  unreadQueryKey,
  type Notification,
} from "@/lib/api/notifications";
import { cn } from "@/lib/cn";
import { useRouter } from "@/lib/i18n/navigation";

function cursorOf(next: string | null | undefined): string | undefined {
  return next ? (new URL(next, "http://x").searchParams.get("cursor") ?? undefined) : undefined;
}

function useRelativeTime() {
  const locale = useLocale();
  const format = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  return (iso: string) => {
    const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60_000);
    if (Math.abs(minutes) < 60) return format.format(minutes, "minute");
    const hours = Math.round(minutes / 60);
    if (Math.abs(hours) < 24) return format.format(hours, "hour");
    return format.format(Math.round(hours / 24), "day");
  };
}

/** The list of in-app notifications, newest first, with "mark everything as read". */
export function NotificationList() {
  const t = useTranslations("notifications");
  const router = useRouter();
  const queryClient = useQueryClient();
  const relative = useRelativeTime();
  const query = useInfiniteQuery({
    queryKey: notificationsQueryKey,
    queryFn: ({ pageParam }) => listNotifications(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => cursorOf(page.next),
  });

  const items = query.data?.pages.flatMap((page) => page.results) ?? [];
  const unread = items.filter((item) => !item.read);

  const refresh = async (unreadCount: number) => {
    queryClient.setQueryData(unreadQueryKey, { unread: unreadCount });
    await queryClient.invalidateQueries({ queryKey: notificationsQueryKey, exact: true });
  };

  const open = async (item: Notification) => {
    if (!item.read) await refresh((await markRead([item.id])).unread);
    if (item.link) router.push(item.link);
  };

  if (query.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<BellSimpleSlash size={48} weight="duotone" />}
        title={t("emptyTitle")}
        description={t("emptyText")}
      />
    );
  }

  return (
    <section aria-labelledby="list-title" className="flex flex-col gap-3">
      <div className="flex flex-col items-start gap-1">
        <h2 id="list-title" className="text-title font-bold">
          {t("listTitle")}
        </h2>
        {unread.length > 0 && (
          <Button
            variant="quiet"
            icon={<Checks size={22} weight="bold" />}
            onClick={async () => refresh((await markRead()).unread)}
          >
            {t("markAll")}
          </Button>
        )}
      </div>
      <ul className="flex flex-col gap-2">
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => void open(item)}
              className={cn(
                "rounded-card flex w-full items-start gap-3 border p-4 text-left",
                item.read ? "border-trait bg-carte" : "border-hibiscus bg-poudre",
              )}
            >
              <span className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="flex flex-wrap items-center gap-2">
                  {!item.read && (
                    <span className="bg-hibiscus text-sur-hibiscus text-mention rounded-full px-2 font-bold">
                      {t("new")}
                    </span>
                  )}
                  <span className="font-bold">{item.title}</span>
                </span>
                {item.body && <span className="text-prune-doux">{item.body}</span>}
                <span className="text-mention text-prune-doux">{relative(item.created_at)}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {query.hasNextPage && (
        <Button
          variant="secondary"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {t("more")}
        </Button>
      )}
    </section>
  );
}
