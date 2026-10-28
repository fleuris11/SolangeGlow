"use client";

import { Broadcast, CalendarBlank, Clock, DoorOpen, UsersThree } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { getLiveRoom, getLives, registerLive, unregisterLive, type Live } from "@/lib/api/academy";
import { ApiError, hasSession } from "@/lib/api/client";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { Link, usePathname, useRouter } from "@/lib/i18n/navigation";

function when(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale, {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

/** The training lives to come: register, then enter the room a few minutes before. */
export function LivesScreen() {
  const t = useTranslations("academy.lives");
  const query = useQuery({ queryKey: ["academy-lives"], queryFn: getLives });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <Broadcast aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={`${t("title")}. ${t("intro")}`} />
      </div>
      <p>{t("intro")}</p>
      {query.isPending ? (
        <Skeleton className="h-48 rounded-2xl" />
      ) : !query.data ? (
        <p role="alert" className="font-bold">
          {query.error instanceof ApiError ? query.error.message : t("error")}
        </p>
      ) : !query.data.open ? (
        <EmptyState icon={<Broadcast size={44} weight="duotone" />} title={t("closed")} />
      ) : query.data.results.length === 0 ? (
        <EmptyState
          icon={<Broadcast size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
          action={
            <Link href="/academie" className={buttonClasses({ variant: "secondary" })}>
              {t("courses")}
            </Link>
          }
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {query.data.results.map((live) => (
            <li key={live.id}>
              <LiveCard live={live} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function LiveCard({ live }: { live: Live }) {
  const t = useTranslations("academy.lives");
  const locale = useLocale();
  return (
    <article className="border-trait bg-carte rounded-card flex flex-col gap-2 border p-4">
      <h2 className="text-lead font-bold">{live.title}</h2>
      <p className="text-small text-prune-doux">{t("by", { name: live.trainer_name })}</p>
      <p className="flex items-center gap-2">
        <CalendarBlank aria-hidden size={20} />
        {when(live.starts_at, locale)}
      </p>
      <p className="text-small text-prune-doux flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="inline-flex items-center gap-1">
          <Clock aria-hidden size={18} />
          {t("minutes", { count: live.duration_minutes })}
        </span>
        <span className="inline-flex items-center gap-1">
          <UsersThree aria-hidden size={18} />
          {t("placesLeft", { count: live.places_left })}
        </span>
      </p>
      {live.registered && <p className="text-feuille font-bold">{t("registered")}</p>}
      <Link
        href={`/academie/live/${live.id}`}
        className={buttonClasses({
          variant: live.registered ? "primary" : "secondary",
          fullWidth: true,
        })}
      >
        {live.registered ? t("openRoom") : t("see")}
      </Link>
    </article>
  );
}

/** The waiting room: countdown, registration, and the door that opens before the start. */
export function LiveRoomScreen({ liveId }: { liveId: string }) {
  const t = useTranslations("academy.lives");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const signedIn = hasSession();
  const query = useQuery({
    queryKey: ["academy-live", liveId],
    queryFn: () => getLiveRoom(liveId),
    enabled: signedIn,
    refetchInterval: 30_000,
  });
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  if (!signedIn) {
    return (
      <div className="flex flex-col gap-4">
        <p className="font-bold">{t("signIn")}</p>
        <Button
          size="lg"
          fullWidth
          onClick={() => {
            rememberReturnPath(pathname);
            router.push("/auth?as=client");
          }}
        >
          {t("signInCta")}
        </Button>
      </div>
    );
  }
  if (query.isPending) return <Skeleton className="h-64 rounded-2xl" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const room = query.data;
  const live = room.live;
  const left = Math.max(0, Math.floor((new Date(live.starts_at).getTime() - now) / 1000));
  const days = Math.floor(left / 86_400);
  const hours = Math.floor((left % 86_400) / 3600);
  const minutes = Math.floor((left % 3600) / 60);
  const seconds = left % 60;
  const open =
    room.open ||
    (room.registered &&
      now >= new Date(room.opens_at).getTime() &&
      now < new Date(room.ends_at).getTime());

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: ["academy-live", liveId] });
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  const ended = live.status === "ended";

  return (
    <article className="flex flex-col gap-6">
      <Link
        href="/academie/lives"
        className="text-prune-doux inline-flex min-h-12 items-center gap-2 self-start font-bold"
      >
        {t("all")}
      </Link>
      <header className="flex flex-col gap-2">
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex-1 font-bold">{live.title}</h1>
          <SpeakButton text={`${live.title}. ${when(live.starts_at, locale)}`} />
        </div>
        <p className="text-prune-doux">{t("by", { name: live.trainer_name })}</p>
        <p className="flex items-center gap-2 font-bold">
          <CalendarBlank aria-hidden size={22} />
          {when(live.starts_at, locale)}
        </p>
        {live.description && <p className="whitespace-pre-line">{live.description}</p>}
        {live.course_slug && (
          <Link href={`/academie/${live.course_slug}`} className="underline">
            {t("course", { title: live.course_title ?? "" })}
          </Link>
        )}
      </header>

      {live.status === "cancelled" ? (
        <p className="border-alerte rounded-2xl border-2 p-3 font-bold">{t("cancelled")}</p>
      ) : (
        <section
          aria-live="polite"
          className="bg-poudre flex flex-col items-center gap-3 rounded-2xl p-5 text-center"
        >
          <DoorOpen aria-hidden size={44} weight="duotone" className="text-hibiscus" />
          {ended ? (
            <p className="text-title font-bold">{t("over")}</p>
          ) : left > 0 ? (
            <p className="text-title font-bold">
              {days > 0
                ? t("countdownDays", { days, hours })
                : t("countdown", {
                    hours: String(hours),
                    minutes: String(minutes).padStart(2, "0"),
                    seconds: String(seconds).padStart(2, "0"),
                  })}
            </p>
          ) : (
            <p className="text-title font-bold">{t("started")}</p>
          )}
          {ended && <p>{t("replayHint")}</p>}
          {open && !ended && !room.broadcast_ready && <p>{t("comingSoon")}</p>}
          {!open && room.registered && <p>{t("opensBefore")}</p>}
        </section>
      )}

      {live.status !== "cancelled" &&
        (room.registered ? (
          <div className="flex flex-col gap-3">
            {ended || open || room.host ? (
              <Link
                href={room.room_link}
                className={buttonClasses({ size: "lg", fullWidth: true })}
              >
                <DoorOpen aria-hidden size={24} weight="bold" />
                {ended ? t("replay") : room.host ? t("hostRoom") : t("join")}
              </Link>
            ) : (
              <Button size="lg" fullWidth disabled>
                <DoorOpen aria-hidden size={24} weight="bold" />
                {t("join")}
              </Button>
            )}
            {!room.host && !ended && (
              <Button
                variant="quiet"
                fullWidth
                disabled={busy}
                onClick={() => void run(() => unregisterLive(liveId))}
              >
                {t("unregister")}
              </Button>
            )}
          </div>
        ) : (
          <Button
            size="lg"
            fullWidth
            disabled={busy || live.places_left === 0}
            onClick={() => void run(() => registerLive(liveId))}
          >
            {live.places_left === 0 ? t("full") : t("register")}
          </Button>
        ))}
    </article>
  );
}
