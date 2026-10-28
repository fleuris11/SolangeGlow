"use client";

import { Phone, PhoneSlash, VideoCamera } from "@phosphor-icons/react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { getCallLog } from "@/lib/api/calls";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

/** « My calls »: who, when, how long, missed. Each line opens the conversation. */
export function CallLog() {
  const t = useTranslations("calls");
  const locale = useLocale();
  const query = useInfiniteQuery({
    queryKey: ["call-log"],
    queryFn: ({ pageParam }) => getCallLog(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next ?? undefined,
  });
  const calls = query.data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <section className="flex flex-col gap-6">
      <header className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("log.title")}</h1>
        <SpeakButton text={t("log.title")} />
      </header>
      {query.isPending && <Skeleton className="rounded-card h-40" />}
      {query.isSuccess && calls.length === 0 && (
        <EmptyState
          icon={<Phone aria-hidden size={48} weight="duotone" />}
          title={t("log.empty")}
          action={
            <Link href="/messages" className="font-bold underline">
              {t("backToMessages")}
            </Link>
          }
        />
      )}
      <ul className="flex flex-col gap-2">
        {calls.map((call) => {
          const other = call.people[0];
          const missed = call.status !== "ended";
          const Icon = missed ? PhoneSlash : call.kind === "video" ? VideoCamera : Phone;
          const name = call.is_dispute ? t("disputeCall") : (other?.name ?? t("someone"));
          const minutes = Math.max(1, Math.round(call.duration_seconds / 60));
          return (
            <li key={call.id}>
              <Link
                href={`/messages/${call.conversation_id}`}
                className="border-trait hover:bg-poudre flex min-h-16 items-center gap-3 rounded-2xl border p-3"
              >
                <Avatar name={name} src={mediaSrc(other?.photo, "thumb")} size="sm" />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate font-bold">{name}</span>
                  <span className="text-small text-prune-doux">
                    {new Intl.DateTimeFormat(locale, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(call.created_at))}
                  </span>
                </span>
                <span
                  className={`text-small flex shrink-0 items-center gap-1 font-bold ${missed ? "text-alerte" : ""}`}
                >
                  <Icon aria-hidden size={20} weight="bold" />
                  {missed
                    ? t(call.mine ? "line.noAnswer" : "line.missed")
                    : t("log.minutes", { minutes })}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
      {query.hasNextPage && (
        <Button
          variant="quiet"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {t("log.older")}
        </Button>
      )}
    </section>
  );
}
