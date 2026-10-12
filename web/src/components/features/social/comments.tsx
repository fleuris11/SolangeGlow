"use client";

import { ArrowBendDownRight, Flag, PaperPlaneRight, Trash } from "@phosphor-icons/react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError, hasSession } from "@/lib/api/client";
import {
  addComment,
  deleteComment,
  getComments,
  report,
  type Comment,
  type Reply,
} from "@/lib/api/social";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { timeAgo } from "./time-ago";

function cursorOf(next: string | null | undefined) {
  return next ?? undefined;
}

/** Comments of a post, with one level of replies. Signed in to write. */
export function Comments({ postId }: { postId: string }) {
  const t = useTranslations("social.comments");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = ["comments", postId];
  const query = useInfiniteQuery({
    queryKey: key,
    queryFn: ({ pageParam }) => getComments(postId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => cursorOf(page.next),
  });
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<Comment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const signedIn = typeof document !== "undefined" && hasSession();

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(undefined);
    try {
      await addComment(postId, text.trim(), replyTo?.id);
      setText("");
      setReplyTo(null);
      await queryClient.invalidateQueries({ queryKey: key });
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    await deleteComment(id);
    await queryClient.invalidateQueries({ queryKey: key });
  };

  const flag = async (id: string) => {
    try {
      await report("comment", id, "harassment");
      toast(t("reported"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  const item = (comment: Comment | Reply, isReply: boolean) => (
    <div className="flex gap-3">
      <Avatar name={comment.author.name} src={mediaSrc(comment.author.photo, "thumb")} size="sm" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p>
          <span className="font-bold">{comment.author.name}</span>{" "}
          <span className="text-mention text-prune-doux">
            {timeAgo(comment.created_at, locale)}
          </span>
        </p>
        <p className="whitespace-pre-line">{comment.text}</p>
        <div className="-ml-2 flex flex-wrap">
          {!isReply && signedIn && (
            <Button variant="quiet" onClick={() => setReplyTo(comment as Comment)}>
              <ArrowBendDownRight aria-hidden size={20} />
              {t("reply")}
            </Button>
          )}
          {comment.is_mine ? (
            <Button variant="quiet" onClick={() => void remove(comment.id)}>
              <Trash aria-hidden size={20} />
              {t("delete")}
            </Button>
          ) : (
            signedIn && (
              <Button variant="quiet" onClick={() => void flag(comment.id)}>
                <Flag aria-hidden size={20} />
                {t("report")}
              </Button>
            )
          )}
        </div>
      </div>
    </div>
  );

  const comments = query.data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <section id="comments" aria-labelledby="comments-title" className="flex flex-col gap-4">
      <h2 id="comments-title" className="text-title font-bold">
        {t("title")}
      </h2>
      {query.isSuccess && comments.length === 0 && <p className="text-prune-doux">{t("empty")}</p>}
      <ul className="flex flex-col gap-4">
        {comments.map((comment) => (
          <li key={comment.id} className="flex flex-col gap-3">
            {item(comment, false)}
            {comment.replies.length > 0 && (
              <ul className="border-trait ml-6 flex flex-col gap-3 border-l-2 pl-4">
                {comment.replies.map((reply) => (
                  <li key={reply.id}>{item(reply, true)}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
      {query.hasNextPage && (
        <Button variant="secondary" onClick={() => void query.fetchNextPage()}>
          {t("more")}
        </Button>
      )}

      {signedIn ? (
        <form onSubmit={(event) => void send(event)} className="flex flex-col gap-2">
          {replyTo && (
            <p className="text-small text-prune-doux">
              {t("replyingTo", { name: replyTo.author.name })}{" "}
              <button
                type="button"
                className="font-bold underline"
                onClick={() => setReplyTo(null)}
              >
                {t("cancel")}
              </button>
            </p>
          )}
          <label htmlFor="comment-text" className="font-bold">
            {replyTo ? t("yourReply") : t("yourComment")}
          </label>
          <textarea
            id="comment-text"
            rows={2}
            maxLength={1000}
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 py-3 outline-none"
          />
          {error && (
            <p role="alert" className="text-alerte font-bold">
              {error}
            </p>
          )}
          <Button type="submit" disabled={busy || !text.trim()}>
            <PaperPlaneRight aria-hidden size={22} weight="bold" />
            {t("send")}
          </Button>
        </form>
      ) : (
        <Link href="/auth" className="text-hibiscus font-bold underline">
          {t("signIn")}
        </Link>
      )}
    </section>
  );
}
