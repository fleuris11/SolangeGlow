"use client";

import {
  ArrowLeft,
  Broadcast,
  CameraRotate,
  CheckCircle,
  Eye,
  HandWaving,
  Microphone,
  MicrophoneSlash,
  PaperPlaneRight,
  PushPin,
  ShoppingBag,
  SpeakerHigh,
  StopCircle,
  VideoCamera,
  VideoCameraSlash,
  WifiLow,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useReducer, useRef, useState, type ReactNode } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button, buttonClasses } from "@/components/ui/button";
import { PriceTag } from "@/components/ui/price-tag";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  askQuestion,
  endLive,
  getLive,
  giveFloor,
  joinLive,
  lowerHand,
  markAnswered,
  pinProduct,
  raiseHand,
  startLive,
  takeFloor,
  unpinProduct,
  type LiveKind,
  type LivePin,
  type LiveState,
} from "@/lib/api/live";
import { getMyProducts } from "@/lib/api/shop";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { cn } from "@/lib/cn";
import { Link, usePathname, useRouter } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { usePreferences } from "@/lib/preferences/preferences-provider";
import { RtcSession, weakNetwork, type RtcEvent } from "@/lib/rtc/room";

import { TrackView } from "../rtc/track-view";
import { BuySheet } from "./buy-sheet";

function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const rest = String(s % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${rest}` : `${m}:${rest}`;
}

function Chip({ children, tone = "carte" }: { children: ReactNode; tone?: "carte" | "live" }) {
  return (
    <span
      className={cn(
        "text-small inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-bold",
        tone === "live" ? "bg-hibiscus text-sur-hibiscus" : "bg-carte/90 text-prune",
      )}
    >
      {children}
    </span>
  );
}

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
          "inline-flex size-12 items-center justify-center rounded-full border-2",
          pressed ? "bg-prune text-lait border-prune" : "border-trait bg-carte",
        )}
      >
        {children}
      </span>
      {label}
    </button>
  );
}

/**
 * The live room (training or sale), phone first: the video on top, then what to do —
 * questions, raised hand, pinned products — and the replay once it is over.
 */
export function LiveRoom({ kind, id }: { kind: LiveKind; id: string }) {
  const t = useTranslations("live");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const { dataSaver } = usePreferences();
  const key = ["live", kind, id];
  const session = useRef<RtcSession | null>(null);
  // One connection at a time, even when two clicks or effects arrive together.
  const busyConnecting = useRef(false);
  const [rtc, setRtc] = useState<RtcSession | null>(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [, refresh] = useReducer((n: number) => n + 1, 0);
  const [now, setNow] = useState(() => Date.now());
  const [weak, setWeak] = useState(false);
  const [audioBlocked, setAudioBlocked] = useState(false);
  const [hostIdentity, setHostIdentity] = useState<string | undefined>();
  const [question, setQuestion] = useState("");
  const [buying, setBuying] = useState<LivePin | null>(null);
  const [picking, setPicking] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [busy, setBusy] = useState(false);
  const replayRef = useRef<HTMLVideoElement>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: () => getLive(kind, id),
    refetchInterval: (q) =>
      q.state.data?.status === "on_air"
        ? 10_000
        : q.state.data?.status === "scheduled"
          ? 20_000
          : false,
    retry: false,
  });
  const live = query.data;

  const reload = useCallback(
    () => void queryClient.invalidateQueries({ queryKey: key }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [kind, id],
  );

  const leave = useCallback(async () => {
    const current = session.current;
    session.current = null;
    await current?.leave();
    setRtc(null);
    setConnected(false);
  }, []);

  const onData = useCallback(
    (event: RtcEvent) => {
      if (event.type === "purchase" && typeof event.product === "string" && event.product) {
        toast(t("sale.bought", { product: event.product }), "success");
      }
      reload();
    },
    [reload, t, toast],
  );

  const connect = useCallback(
    async (host: boolean) => {
      if (session.current || busyConnecting.current) return;
      busyConnecting.current = true;
      setConnecting(true);
      try {
        const access = await joinLive(kind, id);
        setHostIdentity(access.host_identity);
        const created = new RtcSession({
          onChange: refresh,
          onData,
          onWeak: (value) => setWeak(value),
          onAudioBlocked: setAudioBlocked,
          onEnded: () => {
            void leave();
            reload();
          },
        });
        session.current = created;
        setRtc(created);
        const slow = weakNetwork(dataSaver);
        await created.connect(access.url, access.token);
        if (host) {
          await created.setMicrophone(true);
          await created.setCamera(true).catch(() => toast(t("cameraRefused"), "warning"));
        } else if (slow) {
          setWeak(true); // proposed at once: « audio only »
        }
        setConnected(true);
      } catch (error) {
        await leave();
        toast(error instanceof ApiError ? error.message : t("error"), "warning");
      } finally {
        busyConnecting.current = false;
        setConnecting(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [kind, id, dataSaver, onData],
  );

  // On air: everybody who may watch comes in by herself.
  useEffect(() => {
    // After the render (the connection changes the screen).
    const timer = window.setTimeout(() => {
      if (live?.status === "on_air" && (live.can_watch || live.is_host) && !session.current) {
        void connect(live.is_host);
      }
      if (live && live.status !== "on_air" && session.current) void leave();
    });
    return () => window.clearTimeout(timer);
  }, [live, connect, leave]);

  // The floor: her microphone opens when the host gives it, closes when taken back.
  useEffect(() => {
    if (!rtc || !connected || live?.is_host) return;
    if (live?.speaking && rtc.canSpeak && !rtc.micOn)
      void rtc.setMicrophone(true).catch(() => undefined);
    if (!live?.speaking && rtc.micOn) void rtc.setMicrophone(false).catch(() => undefined);
  }, [rtc, live?.speaking, live?.is_host, connected, now]);

  useEffect(() => () => void leave(), [leave]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  if (query.isPending) return <Skeleton className="rounded-card m-4 h-96" />;
  if (query.isError || !live) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <p role="alert" className="font-bold">
          {query.error instanceof ApiError ? query.error.message : t("error")}
        </p>
        <Link href="/" className={buttonClasses({ variant: "secondary" })}>
          {t("homeLink")}
        </Link>
      </div>
    );
  }

  const sale = live.sale;
  const run = async (action: () => Promise<LiveState | unknown>) => {
    setBusy(true);
    try {
      const value = await action();
      if (value && typeof value === "object" && "status" in value) {
        queryClient.setQueryData(key, value as LiveState);
      } else {
        reload();
      }
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };
  const signIn = () => {
    rememberReturnPath(pathname);
    router.push("/auth?as=client");
  };

  const startsIn = (new Date(live.starts_at).getTime() - now) / 1000;
  const canStart = now >= new Date(live.can_start_at).getTime();
  const elapsed = live.started_at ? (now - new Date(live.started_at).getTime()) / 1000 : 0;
  const video = live.is_host ? rtc?.localVideo() : rtc?.remoteVideo(hostIdentity);
  const viewers = Math.max(live.viewers, rtc ? rtc.othersCount - (live.is_host ? 0 : 1) : 0);
  const replay = live.replay;
  const replaySrc = replay?.urls[dataSaver ? "low" : "medium"] ?? replay?.urls.low;
  const hostPhoto = mediaSrc(live.host.photo, "medium");
  const pinned = sale?.pins.filter((p) => p.pinned) ?? [];
  const shownPins = live.status === "on_air" ? pinned : (sale?.pins ?? []);

  return (
    <div className="flex min-h-dvh flex-col gap-4 pb-8">
      <header className="flex items-center gap-2 px-2 pt-2">
        <Link
          href={live.link}
          aria-label={t("back")}
          className="hover:bg-poudre inline-flex size-12 shrink-0 items-center justify-center rounded-full"
        >
          <ArrowLeft aria-hidden size={26} weight="bold" />
        </Link>
        <div className="flex min-w-0 flex-1 flex-col">
          <h1 className="truncate font-bold">{live.title}</h1>
          <p className="text-mention text-prune-doux truncate">
            {t(kind === "sale" ? "bySale" : "byTraining", { name: live.host.name })}
          </p>
        </div>
        <SpeakButton text={live.title} />
      </header>

      {/* The stage: video, waiting screen or replay. */}
      <section
        aria-label={t("stage")}
        className="bg-poudre relative mx-4 flex aspect-[3/4] max-h-[58dvh] flex-col items-center justify-center gap-3 overflow-hidden rounded-[20px] text-center"
      >
        {live.status === "on_air" && video && !rtc?.isAudioOnly ? (
          <TrackView
            track={video}
            mirror={live.is_host}
            label={t("videoOf", { name: live.host.name })}
            className="absolute inset-0"
          />
        ) : live.status === "ended" && replay?.status === "ready" && replaySrc ? (
          <video
            ref={replayRef}
            src={replaySrc}
            poster={replay.urls.poster}
            controls
            playsInline
            preload="metadata"
            aria-label={t("replayOf", { title: live.title })}
            className="absolute inset-0 size-full bg-transparent object-contain"
          />
        ) : (
          <div className="flex flex-col items-center gap-3 px-6">
            <Avatar
              name={live.host.name}
              src={hostPhoto}
              size="lg"
              halo={live.status === "on_air"}
            />
            {live.status === "scheduled" && (
              <>
                <p className="text-title font-bold tabular-nums" aria-live="polite">
                  {startsIn > 0 ? t("startsIn", { time: clock(startsIn) }) : t("startsSoon")}
                </p>
                <p className="text-prune-doux">
                  {new Intl.DateTimeFormat(locale, {
                    dateStyle: "full",
                    timeStyle: "short",
                    timeZone: live.time_zone,
                  }).format(new Date(live.starts_at))}
                </p>
              </>
            )}
            {live.status === "on_air" && (
              <p className="text-title font-bold">
                {rtc?.isAudioOnly
                  ? t("audioOnlyOn")
                  : connecting
                    ? t("connecting")
                    : t("waitingVideo")}
              </p>
            )}
            {live.status === "ended" && (
              <>
                <p className="text-title font-bold">{t("over")}</p>
                <p className="text-prune-doux">
                  {replay?.status === "processing"
                    ? t("replaySoon")
                    : live.can_watch
                      ? t("noReplay")
                      : ""}
                </p>
              </>
            )}
            {live.status === "cancelled" && (
              <p className="text-title font-bold">{t("cancelled")}</p>
            )}
          </div>
        )}

        {live.status === "on_air" && (
          <div className="absolute top-3 left-3 flex flex-wrap gap-2">
            <Chip tone="live">
              <Broadcast aria-hidden size={18} weight="bold" />
              {t("onAir")}
            </Chip>
            <Chip>
              <Eye aria-hidden size={18} weight="bold" />
              <span className="sr-only">{t("viewers", { count: viewers })}</span>
              <span aria-hidden>{viewers}</span>
            </Chip>
            {sale && (
              <Chip>
                <ShoppingBag aria-hidden size={18} weight="bold" />
                {t("sale.orders", { count: sale.orders_count })}
              </Chip>
            )}
          </div>
        )}
        {live.status === "on_air" && live.is_host && (
          <p className="bg-carte/90 absolute right-3 bottom-3 rounded-full px-3 py-1 font-bold tabular-nums">
            {clock(elapsed)}
          </p>
        )}
      </section>

      {/* Banners: weak network, sound blocked, the floor. */}
      {weak && rtc && !rtc.isAudioOnly && live.status === "on_air" && (
        <div role="note" className="bg-poudre mx-4 flex items-center gap-3 rounded-2xl p-3">
          <WifiLow aria-hidden size={28} weight="bold" className="text-alerte shrink-0" />
          <p className="min-w-0 flex-1 font-bold">{t("weak")}</p>
          <Button className="shrink-0" onClick={() => void rtc.setAudioOnly(true)}>
            {t("audioOnly")}
          </Button>
        </div>
      )}
      {rtc?.isAudioOnly && live.status === "on_air" && !live.is_host && (
        <Button variant="secondary" className="mx-4" onClick={() => void rtc.setAudioOnly(false)}>
          <VideoCamera aria-hidden size={22} weight="bold" />
          {t("backToVideo")}
        </Button>
      )}
      {audioBlocked && rtc && (
        <Button
          variant="secondary"
          className="mx-4"
          onClick={() => void rtc.allowAudio().then(() => setAudioBlocked(false))}
        >
          <SpeakerHigh aria-hidden size={22} weight="bold" />
          {t("allowSound")}
        </Button>
      )}
      {live.speaking && (
        <div
          role="status"
          className="border-feuille mx-4 flex items-center gap-3 rounded-2xl border-2 p-3"
        >
          <Microphone aria-hidden size={28} weight="fill" className="text-feuille shrink-0" />
          <p className="min-w-0 flex-1 font-bold">{t("hands.youSpeak")}</p>
          <Button
            variant="secondary"
            className="shrink-0"
            disabled={busy}
            onClick={() => void run(() => lowerHand(kind, id))}
          >
            {t("hands.giveBack")}
          </Button>
        </div>
      )}

      {/* The host: go on air, her camera and micro, end. */}
      {live.is_host && live.status === "scheduled" && (
        <div className="mx-4 flex flex-col gap-2">
          <Button
            size="lg"
            fullWidth
            disabled={busy || !canStart}
            onClick={() => void run(() => startLive(kind, id))}
          >
            <Broadcast aria-hidden size={24} weight="bold" />
            {t("host.start")}
          </Button>
          {!canStart && (
            <p className="text-small text-prune-doux text-center">
              {t("host.startFrom", {
                time: new Intl.DateTimeFormat(locale, {
                  timeStyle: "short",
                  timeZone: live.time_zone,
                }).format(new Date(live.can_start_at)),
              })}
            </p>
          )}
        </div>
      )}
      {live.is_host && live.status === "on_air" && (
        <div className="mx-4 flex flex-col gap-3">
          {rtc && connected && (
            <div className="flex justify-center gap-3">
              <Control
                label={rtc.micOn ? t("host.mute") : t("host.unmute")}
                pressed={!rtc.micOn}
                onClick={() => void rtc.setMicrophone(!rtc.micOn)}
              >
                {rtc.micOn ? (
                  <Microphone aria-hidden size={24} weight="bold" />
                ) : (
                  <MicrophoneSlash aria-hidden size={24} weight="bold" />
                )}
              </Control>
              <Control
                label={rtc.cameraOn ? t("host.cameraOff") : t("host.cameraOn")}
                pressed={!rtc.cameraOn}
                onClick={() =>
                  void rtc
                    .setCamera(!rtc.cameraOn)
                    .catch(() => toast(t("cameraRefused"), "warning"))
                }
              >
                {rtc.cameraOn ? (
                  <VideoCamera aria-hidden size={24} weight="bold" />
                ) : (
                  <VideoCameraSlash aria-hidden size={24} weight="bold" />
                )}
              </Control>
              {rtc.cameraOn && (
                <Control label={t("host.flip")} onClick={() => void rtc.flipCamera()}>
                  <CameraRotate aria-hidden size={24} weight="bold" />
                </Control>
              )}
            </div>
          )}
          {confirmEnd ? (
            <div className="grid grid-cols-2 gap-3">
              <Button variant="secondary" onClick={() => setConfirmEnd(false)}>
                {t("host.keepOn")}
              </Button>
              <Button disabled={busy} onClick={() => void run(() => endLive(kind, id))}>
                {t("host.endConfirm")}
              </Button>
            </div>
          ) : (
            <Button variant="secondary" fullWidth onClick={() => setConfirmEnd(true)}>
              <StopCircle aria-hidden size={22} weight="bold" />
              {t("host.end")}
            </Button>
          )}
        </div>
      )}

      {/* Sales: the pinned products, bought without leaving. */}
      {sale && shownPins.length > 0 && (
        <section aria-labelledby="live-products" className="flex flex-col gap-3 px-4">
          <h2 id="live-products" className="text-lead font-bold">
            {live.status === "on_air" ? t("sale.pinned") : t("sale.shown")}
          </h2>
          <ul className="flex gap-3 overflow-x-auto pb-2">
            {shownPins.map((pin) => (
              <li
                key={pin.product_id}
                className="border-trait bg-carte flex w-56 shrink-0 flex-col gap-2 rounded-2xl border p-3"
              >
                <div className="flex items-center gap-3">
                  {pin.photo ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={mediaSrc(pin.photo, "thumb")}
                      alt=""
                      className="size-14 shrink-0 rounded-xl object-cover"
                    />
                  ) : (
                    <span aria-hidden className="bg-poudre size-14 shrink-0 rounded-xl" />
                  )}
                  <span className="flex min-w-0 flex-col">
                    <span className="line-clamp-2 font-bold">{pin.name}</span>
                    <PriceTag amountMinor={pin.price_minor} currency={pin.currency} />
                  </span>
                </div>
                {live.is_host ? null : (
                  <Button disabled={!pin.in_stock} onClick={() => setBuying(pin)}>
                    <ShoppingBag aria-hidden size={20} weight="bold" />
                    {pin.in_stock ? t("sale.buy") : t("sale.soldOut")}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
      {sale && live.is_host && live.status !== "ended" && live.status !== "cancelled" && (
        <div className="mx-4 flex flex-col gap-2">
          <Button variant="secondary" fullWidth onClick={() => setPicking(true)}>
            <PushPin aria-hidden size={22} weight="bold" />
            {t("sale.pick")}
          </Button>
          {sale.revenue_minor !== null && (
            <p className="text-center font-bold">
              {t("sale.revenue", { count: sale.orders_count })}{" "}
              <PriceTag amountMinor={sale.revenue_minor} currency={sale.currency} />
            </p>
          )}
        </div>
      )}

      {/* Training: raise the hand; the host sees the hands and gives the floor. */}
      {live.can_raise_hand && live.status === "on_air" && !live.speaking && (
        <div className="mx-4">
          {live.my_hand === "raised" ? (
            <Button
              variant="secondary"
              fullWidth
              disabled={busy}
              onClick={() => void run(() => lowerHand(kind, id))}
            >
              <HandWaving aria-hidden size={22} weight="fill" />
              {t("hands.lower")}
            </Button>
          ) : (
            <Button fullWidth disabled={busy} onClick={() => void run(() => raiseHand(kind, id))}>
              <HandWaving aria-hidden size={22} weight="bold" />
              {t("hands.raise")}
            </Button>
          )}
        </div>
      )}
      {live.is_host && live.hands.length > 0 && (
        <section aria-labelledby="live-hands" className="flex flex-col gap-2 px-4">
          <h2 id="live-hands" className="text-lead font-bold">
            {t("hands.title", { count: live.hands.length })}
          </h2>
          <ul className="flex flex-col gap-2">
            {live.hands.map((hand) => (
              <li
                key={hand.user_id}
                className="border-trait flex flex-wrap items-center gap-3 rounded-2xl border p-3"
              >
                <HandWaving
                  aria-hidden
                  size={24}
                  weight="duotone"
                  className="text-hibiscus shrink-0"
                />
                <span className="min-w-28 flex-1 font-bold">
                  {hand.name || t("someone")}
                  {hand.status === "speaking" && (
                    <span className="text-feuille text-small ml-2">{t("hands.speaking")}</span>
                  )}
                </span>
                {hand.status === "speaking" ? (
                  <Button
                    variant="secondary"
                    className="shrink-0"
                    disabled={busy}
                    onClick={() => void run(() => takeFloor(kind, id, hand.user_id))}
                  >
                    {t("hands.takeBack")}
                  </Button>
                ) : (
                  <Button
                    className="shrink-0"
                    disabled={busy}
                    onClick={() => void run(() => giveFloor(kind, id, hand.user_id))}
                  >
                    {t("hands.give")}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Written questions (comments during a sale). */}
      {(live.questions.length > 0 || live.can_ask) && (
        <section aria-labelledby="live-questions" className="flex flex-col gap-3 px-4">
          <h2 id="live-questions" className="text-lead font-bold">
            {t(kind === "sale" ? "questions.titleSale" : "questions.title")}
          </h2>
          {live.can_ask && (
            <form
              className="flex items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                const text = question.trim();
                if (!text) return;
                void run(() => askQuestion(kind, id, text)).then(() => setQuestion(""));
              }}
            >
              <label className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="text-small font-bold">{t("questions.label")}</span>
                <input
                  value={question}
                  maxLength={300}
                  onChange={(event) => setQuestion(event.target.value)}
                  className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-4"
                />
              </label>
              <Button type="submit" className="shrink-0" disabled={busy || !question.trim()}>
                <PaperPlaneRight aria-hidden size={20} weight="bold" />
                {t("questions.send")}
              </Button>
            </form>
          )}
          {!live.signed_in && live.status === "on_air" && (
            <Button variant="quiet" onClick={signIn}>
              {t("questions.signIn")}
            </Button>
          )}
          <ul className="flex flex-col gap-2" aria-live="polite">
            {live.questions.map((item) => (
              <li
                key={item.id}
                className={cn(
                  "flex items-start gap-3 rounded-2xl p-3",
                  item.answered ? "border-feuille bg-carte border-2" : "border-trait border",
                )}
              >
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <p className="text-small text-prune-doux font-bold">
                    {item.name || t("someone")}
                    {live.status === "ended" && replay?.status === "ready" && (
                      <button
                        type="button"
                        className="ml-2 underline"
                        onClick={() => {
                          if (replayRef.current) {
                            replayRef.current.currentTime = item.at_second;
                            void replayRef.current.play().catch(() => undefined);
                          }
                        }}
                      >
                        {t("questions.at", { time: clock(item.at_second) })}
                      </button>
                    )}
                  </p>
                  <p className="break-words">{item.text}</p>
                  {item.held && <p className="text-small text-alerte">{t("questions.held")}</p>}
                </div>
                {item.answered ? (
                  <span className="text-feuille text-small flex shrink-0 items-center gap-1 font-bold">
                    <CheckCircle aria-hidden size={18} weight="fill" />
                    {t("questions.answered")}
                  </span>
                ) : (
                  live.is_host &&
                  live.status === "on_air" && (
                    <Button
                      variant="quiet"
                      className="shrink-0 px-3"
                      disabled={busy}
                      onClick={() => void run(() => markAnswered(kind, id, item.id))}
                    >
                      <CheckCircle aria-hidden size={20} weight="bold" />
                      {t("questions.markAnswered")}
                    </Button>
                  )
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {buying && (
        <BuySheet
          pin={buying}
          liveId={id}
          signedIn={live.signed_in}
          onClose={() => setBuying(null)}
          onSignIn={signIn}
        />
      )}
      {picking && sale && (
        <PinSheet
          liveId={id}
          pins={sale.pins}
          onClose={() => setPicking(false)}
          onChange={reload}
        />
      )}
    </div>
  );
}

/** The host chooses which of her products show under the video. */
function PinSheet({
  liveId,
  pins,
  onClose,
  onChange,
}: {
  liveId: string;
  pins: LivePin[];
  onClose: () => void;
  onChange: () => void;
}) {
  const t = useTranslations("live.sale");
  const toast = useToast();
  const products = useQuery({ queryKey: ["my-products"], queryFn: getMyProducts });
  const onScreen = new Set(pins.filter((p) => p.pinned).map((p) => p.product_id));
  const online = (products.data ?? []).filter((product) => product.status === "published");
  const toggle = async (productId: string) => {
    try {
      if (onScreen.has(productId)) await unpinProduct(liveId, productId);
      else await pinProduct(liveId, productId);
      onChange();
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    }
  };
  return (
    <Sheet
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("pick")}
      description={t("pickHelp")}
    >
      {products.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : online.length === 0 ? (
        <p>{t("noProducts")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {online.map((product) => (
            <li
              key={product.id}
              className="border-trait flex items-center gap-3 rounded-2xl border p-3"
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate font-bold">{product.title}</span>
                <PriceTag amountMinor={product.price_minor} currency={product.currency} />
              </span>
              <Button
                variant={onScreen.has(product.id) ? "secondary" : "primary"}
                className="shrink-0"
                onClick={() => void toggle(product.id)}
              >
                <PushPin
                  aria-hidden
                  size={20}
                  weight={onScreen.has(product.id) ? "fill" : "bold"}
                />
                {onScreen.has(product.id) ? t("unpin") : t("pin")}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Sheet>
  );
}
