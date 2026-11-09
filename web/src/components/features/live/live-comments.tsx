"use client";

import {
  ArrowBendDownRight,
  ChatCircleSlash,
  ChatCircleText,
  PaperPlaneRight,
  Prohibit,
  Trash,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  askQuestion,
  blockInLive,
  removeComment,
  replyToComment,
  setComments,
  type LiveKind,
  type LiveState,
} from "@/lib/api/live";
import { cn } from "@/lib/cn";

type Run = (action: () => Promise<LiveState | unknown>) => Promise<void>;

/**
 * The comments of a live, like a chat: the newest at the top, the host's reply under the
 * comment. The host replies, takes a comment away, blocks its author, turns the comments off.
 */
export function LiveComments({
  kind,
  id,
  live,
  busy,
  run,
  onSignIn,
  onSeek,
}: {
  kind: LiveKind;
  id: string;
  live: LiveState;
  busy: boolean;
  run: Run;
  onSignIn: () => void;
  /** In the replay: jump to the moment of the comment. */
  onSeek?: (second: number) => void;
}) {
  const t = useTranslations("live.comments");
  const [text, setText] = useState("");
  const [replying, setReplying] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const onAir = live.status === "on_air";
  const canWrite = live.can_ask || (live.is_host && onAir);

  return (
    <section aria-labelledby="live-comments" className="flex flex-col gap-3 px-4">
      <div className="flex items-center justify-between gap-2">
        <h2 id="live-comments" className="text-lead font-bold">
          {t("title")}
        </h2>
        {live.is_host && onAir && (
          <Button
            variant="quiet"
            className="px-3"
            disabled={busy}
            onClick={() => void run(() => setComments(kind, id, !live.comments_off))}
          >
            {live.comments_off ? (
              <ChatCircleText aria-hidden size={20} weight="bold" />
            ) : (
              <ChatCircleSlash aria-hidden size={20} weight="bold" />
            )}
            {live.comments_off ? t("turnOn") : t("turnOff")}
          </Button>
        )}
      </div>

      {live.comments_off && onAir && (
        <p role="status" className="bg-poudre rounded-2xl p-3 font-semibold">
          {live.is_host ? t("offForAll") : t("offForNow")}
        </p>
      )}

      {canWrite && (
        <form
          className="flex items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            const value = text.trim();
            if (!value) return;
            void run(() => askQuestion(kind, id, value)).then(() => setText(""));
          }}
        >
          <input
            value={text}
            maxLength={300}
            onChange={(event) => setText(event.target.value)}
            aria-label={t("label")}
            placeholder={live.is_host ? t("placeholderHost") : t("placeholder")}
            className="bg-poudre min-h-12 min-w-0 flex-1 rounded-full px-5"
          />
          <Button
            type="submit"
            className="size-12 shrink-0 rounded-full p-0"
            disabled={busy || !text.trim()}
            aria-label={t("send")}
          >
            <PaperPlaneRight aria-hidden size={22} weight="fill" />
          </Button>
        </form>
      )}
      {!live.signed_in && onAir && (
        <Button variant="quiet" onClick={onSignIn}>
          {t("signIn")}
        </Button>
      )}

      <ul className="flex flex-col gap-2" aria-live="polite">
        {live.questions.map((item) => (
          <li key={item.id} className="flex flex-col gap-1">
            <div className={cn("bg-poudre rounded-2xl px-4 py-2.5", item.held && "opacity-70")}>
              <p className="text-small font-bold">
                {item.name || t("someone")}
                {onSeek && (
                  <button
                    type="button"
                    className="text-prune-doux ml-2 font-semibold underline"
                    onClick={() => onSeek(item.at_second)}
                  >
                    {t("at", {
                      time: `${Math.floor(item.at_second / 60)}:${String(item.at_second % 60).padStart(2, "0")}`,
                    })}
                  </button>
                )}
              </p>
              <p className="break-words">{item.text}</p>
              {item.held && <p className="text-small text-alerte">{t("held")}</p>}
            </div>
            {item.reply && (
              <div className="ml-6 flex items-start gap-2">
                <ArrowBendDownRight aria-hidden size={18} className="mt-2.5 shrink-0" />
                <div className="bg-carte border-trait rounded-2xl border px-4 py-2.5">
                  <p className="text-small font-bold">{t("replyOf", { name: live.host.name })}</p>
                  <p className="break-words">{item.reply}</p>
                </div>
              </div>
            )}
            {live.is_host && onAir && !item.mine && (
              <div className="ml-2 flex flex-wrap gap-1">
                <Button
                  variant="quiet"
                  className="min-h-9 px-2"
                  onClick={() => {
                    setReplying(replying === item.id ? null : item.id);
                    setAnswer("");
                  }}
                >
                  <ArrowBendDownRight aria-hidden size={18} weight="bold" />
                  {t("reply")}
                </Button>
                <Button
                  variant="quiet"
                  className="min-h-9 px-2"
                  disabled={busy}
                  onClick={() => void run(() => removeComment(kind, id, item.id))}
                >
                  <Trash aria-hidden size={18} weight="bold" />
                  {t("remove")}
                </Button>
                {item.author_id && (
                  <Button
                    variant="quiet"
                    className="min-h-9 px-2"
                    disabled={busy}
                    onClick={() => {
                      if (window.confirm(t("blockConfirm", { name: item.name || t("someone") }))) {
                        void run(() => blockInLive(kind, id, item.author_id!));
                      }
                    }}
                  >
                    <Prohibit aria-hidden size={18} weight="bold" />
                    {t("block")}
                  </Button>
                )}
              </div>
            )}
            {replying === item.id && (
              <form
                className="ml-6 flex items-center gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  const value = answer.trim();
                  if (!value) return;
                  void run(() => replyToComment(kind, id, item.id, value)).then(() => {
                    setReplying(null);
                    setAnswer("");
                  });
                }}
              >
                <input
                  autoFocus
                  value={answer}
                  maxLength={300}
                  onChange={(event) => setAnswer(event.target.value)}
                  aria-label={t("replyLabel", { name: item.name || t("someone") })}
                  className="bg-carte border-trait min-h-11 min-w-0 flex-1 rounded-full border px-4"
                />
                <Button type="submit" className="shrink-0" disabled={busy || !answer.trim()}>
                  {t("replySend")}
                </Button>
              </form>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
