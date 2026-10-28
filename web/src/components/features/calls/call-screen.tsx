"use client";

import {
  ArrowLeft,
  CameraRotate,
  Microphone,
  MicrophoneSlash,
  Phone,
  PhoneDisconnect,
  SpeakerHigh,
  VideoCamera,
  VideoCameraSlash,
  WifiLow,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useReducer, useRef, useState, type ReactNode } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { answerCall, declineCall, getCall, hangUp, type Call } from "@/lib/api/calls";
import { ApiError } from "@/lib/api/client";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { subscribe } from "@/lib/messaging/bus";
import { usePreferences } from "@/lib/preferences/preferences-provider";
import { RtcSession, weakNetwork } from "@/lib/rtc/room";
import { cn } from "@/lib/cn";

import { TrackView } from "../rtc/track-view";

const OPEN = ["ringing", "ongoing"];

function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** A round button with its word under it (micro, camera, audio only). */
function Control({
  label,
  pressed,
  onClick,
  children,
}: {
  label: string;
  pressed?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className="text-mention flex min-w-16 flex-col items-center gap-1 font-bold"
    >
      <span
        className={cn(
          "inline-flex size-14 items-center justify-center rounded-full border-2",
          pressed ? "bg-prune text-lait border-prune" : "border-trait bg-carte",
        )}
      >
        {children}
      </span>
      {label}
    </button>
  );
}

/** The call: ringing, answering, talking (audio or video), over. No phone number anywhere. */
export function CallScreen({ callId }: { callId: string }) {
  const t = useTranslations("calls");
  const toast = useToast();
  const queryClient = useQueryClient();
  const params = useSearchParams();
  const { dataSaver } = usePreferences();
  const session = useRef<RtcSession | null>(null);
  // One connection at a time, even when two clicks or effects arrive together.
  const busyConnecting = useRef(false);
  const [rtc, setRtc] = useState<RtcSession | null>(null);
  const [connected, setConnected] = useState(false);
  const [joining, setJoining] = useState(false);
  const [, refresh] = useReducer((n: number) => n + 1, 0);
  const [now, setNow] = useState(() => Date.now());
  const [weak, setWeak] = useState(false);
  const [audioBlocked, setAudioBlocked] = useState(false);
  const autoAnswered = useRef(false);
  const key = ["call", callId];

  const query = useQuery({
    queryKey: key,
    queryFn: () => getCall(callId),
    refetchInterval: (q) => (OPEN.includes(q.state.data?.status ?? "") ? 3_000 : false),
    retry: false,
  });
  const call = query.data;
  const over = !!call && !OPEN.includes(call.status);

  const leave = useCallback(async () => {
    const current = session.current;
    session.current = null;
    await current?.leave();
    setRtc(null);
    setConnected(false);
  }, []);

  const connect = useCallback(
    async (answer: () => Promise<{ call: Call; access: { url: string; token: string } }>) => {
      if (session.current || busyConnecting.current) return;
      busyConnecting.current = true;
      setJoining(true);
      try {
        const joined = await answer();
        queryClient.setQueryData(key, joined.call);
        const created = new RtcSession({
          onChange: refresh,
          onWeak: setWeak,
          onAudioBlocked: setAudioBlocked,
          onEnded: () => {
            void leave();
            void queryClient.invalidateQueries({ queryKey: key });
          },
        });
        session.current = created;
        setRtc(created);
        const audioOnly = joined.call.kind === "audio";
        await created.connect(joined.access.url, joined.access.token, { audioOnly });
        await created.setMicrophone(true);
        if (joined.call.kind === "video") {
          if (weakNetwork(dataSaver)) setWeak(true);
          else await created.setCamera(true).catch(() => toast(t("cameraRefused"), "warning"));
        }
        setConnected(true);
      } catch (error) {
        await leave();
        const message =
          error instanceof ApiError
            ? error.message
            : error instanceof DOMException && error.name === "NotAllowedError"
              ? t("micRefused")
              : t("error");
        toast(message, "warning");
      } finally {
        busyConnecting.current = false;
        setJoining(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [callId, dataSaver],
  );

  // The caller (or someone who reloads the page) comes straight in; « ?answer=1 » answers.
  useEffect(() => {
    if (!call || autoAnswered.current || !OPEN.includes(call.status)) return;
    const inCall = call.my_state === "joined";
    const answerAsked = params.get("answer") === "1" && call.my_state === "invited";
    if (!inCall && !answerAsked) return;
    // After the render (the connection changes the screen).
    const timer = window.setTimeout(() => {
      autoAnswered.current = true;
      void connect(() => answerCall(callId));
    });
    return () => window.clearTimeout(timer);
  }, [call, callId, connect, params]);

  // Over (hung up, declined, missed): leave the room.
  useEffect(() => {
    if (!over) return;
    const timer = window.setTimeout(() => void leave());
    return () => window.clearTimeout(timer);
  }, [over, leave]);

  useEffect(() => () => void leave(), [leave]);

  useEffect(
    () =>
      subscribe((event) => {
        if ((event.type === "call" || event.type === "call_incoming") && event.call.id === callId) {
          void queryClient.invalidateQueries({ queryKey: key });
        }
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [callId],
  );

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  if (query.isPending) return <Skeleton className="rounded-card m-4 h-96" />;
  if (query.isError || !call) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <p role="alert" className="font-bold">
          {query.error instanceof ApiError ? query.error.message : t("error")}
        </p>
        <Link href="/messages" className={buttonClasses({ variant: "secondary" })}>
          {t("backToMessages")}
        </Link>
      </div>
    );
  }

  const other = call.mine
    ? call.people[0]
    : (call.people.find((p) => p.id === call.caller_id) ?? call.people[0]);
  const name = call.is_dispute ? t("disputeCall") : (other?.name ?? t("someone"));
  const ringingForMe = call.status === "ringing" && call.my_state === "invited" && !connected;
  const video = call.kind === "video";
  const remote = rtc?.remoteVideo();
  const local = rtc?.localVideo();
  const talking = call.answered_at ? (now - new Date(call.answered_at).getTime()) / 1000 : 0;
  const leftSeconds = call.ends_by ? (new Date(call.ends_by).getTime() - now) / 1000 : Infinity;

  const status = over
    ? call.status === "ended"
      ? t("endedAfter", { time: clock(talking) })
      : t(`status.${call.status}`)
    : ringingForMe
      ? video
        ? t("incomingVideo")
        : t("incomingAudio")
      : call.status === "ringing"
        ? t("ringing")
        : rtc?.reconnecting
          ? t("reconnecting")
          : connected
            ? clock(talking)
            : t("connecting");

  const hang = async () => {
    await leave();
    try {
      queryClient.setQueryData(key, await hangUp(callId));
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    }
  };

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex items-center gap-2 px-2 py-2">
        <Link
          href={`/messages/${call.conversation_id}`}
          aria-label={t("back")}
          className="hover:bg-poudre inline-flex size-12 items-center justify-center rounded-full"
        >
          <ArrowLeft aria-hidden size={26} weight="bold" />
        </Link>
        <h1 className="flex-1 truncate font-bold">{video ? t("videoCall") : t("audioCall")}</h1>
      </header>

      <section
        aria-live="polite"
        className="relative mx-4 flex flex-1 flex-col items-center justify-center gap-4 overflow-hidden rounded-[20px]"
      >
        {video && remote && !over ? (
          <TrackView track={remote} label={t("videoOf", { name })} className="absolute inset-0" />
        ) : (
          <>
            <Avatar
              name={name}
              src={mediaSrc(other?.photo, "medium")}
              size="xl"
              halo={!over && call.status === "ringing"}
            />
            <p className="text-headline text-center font-bold">{name}</p>
          </>
        )}
        <p
          className={cn(
            "text-title font-bold tabular-nums",
            video &&
              remote &&
              !over &&
              "bg-carte/90 text-body absolute top-3 left-3 rounded-full px-3 py-1",
          )}
        >
          {status}
        </p>
        {call.is_dispute && !over && (
          <ul className="text-small text-prune-doux flex flex-wrap justify-center gap-2">
            {call.people.map((person) => (
              <li key={person.id} className="bg-poudre rounded-full px-3 py-1">
                {person.name} {person.state === "joined" ? t("here") : ""}
              </li>
            ))}
          </ul>
        )}
        {video && local && !over && (
          // Over the other camera in a corner; under the name while it rings.
          <div
            className={cn(
              "border-carte h-36 w-24 overflow-hidden rounded-2xl border-2",
              remote ? "absolute right-3 bottom-3" : "relative",
            )}
          >
            <TrackView track={local} mirror label={t("myCamera")} />
          </div>
        )}
        {connected && leftSeconds < 120 && (
          <p className="bg-carte/90 absolute bottom-3 left-3 rounded-full px-3 py-1 font-bold">
            {t("endsSoon", { time: clock(leftSeconds) })}
          </p>
        )}
      </section>

      {weak && video && rtc && !rtc.isAudioOnly && !over && (
        <div role="note" className="bg-poudre mx-4 mt-3 flex items-center gap-3 rounded-2xl p-3">
          <WifiLow aria-hidden size={28} weight="bold" className="text-alerte shrink-0" />
          <p className="min-w-0 flex-1 font-bold">{t("weak")}</p>
          <Button className="shrink-0" onClick={() => void rtc.setAudioOnly(true)}>
            {t("audioOnly")}
          </Button>
        </div>
      )}
      {audioBlocked && rtc && (
        <Button
          variant="secondary"
          className="mx-4 mt-3"
          onClick={() => void rtc.allowAudio().then(() => setAudioBlocked(false))}
        >
          <SpeakerHigh aria-hidden size={22} weight="bold" />
          {t("allowSound")}
        </Button>
      )}

      <footer className="pb-safe flex flex-col gap-4 px-4 pt-4 pb-6">
        {over ? (
          <Link
            href={`/messages/${call.conversation_id}`}
            className={buttonClasses({ size: "lg", fullWidth: true })}
          >
            {t("backToChat")}
          </Link>
        ) : ringingForMe ? (
          <div className="grid grid-cols-2 gap-3">
            <Button
              variant="secondary"
              size="lg"
              onClick={() =>
                void declineCall(callId)
                  .then((value) => queryClient.setQueryData(key, value))
                  .catch(() => toast(t("error"), "warning"))
              }
            >
              <PhoneDisconnect aria-hidden size={24} weight="bold" />
              {t("decline")}
            </Button>
            <Button
              size="lg"
              disabled={joining}
              onClick={() => void connect(() => answerCall(callId))}
            >
              <Phone aria-hidden size={24} weight="fill" />
              {t("answer")}
            </Button>
          </div>
        ) : (
          <>
            {rtc && connected && (
              <div className="flex justify-center gap-4">
                <Control
                  label={rtc.micOn ? t("mute") : t("unmute")}
                  pressed={!rtc.micOn}
                  onClick={() => void rtc.setMicrophone(!rtc.micOn)}
                >
                  {rtc.micOn ? (
                    <Microphone aria-hidden size={26} weight="bold" />
                  ) : (
                    <MicrophoneSlash aria-hidden size={26} weight="bold" />
                  )}
                </Control>
                {video && (
                  <Control
                    label={rtc.cameraOn ? t("cameraOff") : t("cameraOn")}
                    pressed={!rtc.cameraOn}
                    onClick={() =>
                      void rtc
                        .setCamera(!rtc.cameraOn)
                        .catch(() => toast(t("cameraRefused"), "warning"))
                    }
                  >
                    {rtc.cameraOn ? (
                      <VideoCamera aria-hidden size={26} weight="bold" />
                    ) : (
                      <VideoCameraSlash aria-hidden size={26} weight="bold" />
                    )}
                  </Control>
                )}
                {video && rtc.cameraOn && (
                  <Control label={t("flip")} onClick={() => void rtc.flipCamera()}>
                    <CameraRotate aria-hidden size={26} weight="bold" />
                  </Control>
                )}
                {video && (
                  <Control
                    label={t("audioOnly")}
                    pressed={rtc.isAudioOnly}
                    onClick={() => void rtc.setAudioOnly(!rtc.isAudioOnly)}
                  >
                    <WifiLow aria-hidden size={26} weight="bold" />
                  </Control>
                )}
              </div>
            )}
            <Button size="lg" fullWidth onClick={() => void hang()}>
              <PhoneDisconnect aria-hidden size={24} weight="fill" />
              {call.status === "ringing" && call.mine ? t("cancel") : t("hangUp")}
            </Button>
          </>
        )}
      </footer>
    </div>
  );
}
