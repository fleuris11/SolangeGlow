"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState, type ReactNode } from "react";

import { useToast } from "@/components/ui/toast";
import { hasSession } from "@/lib/api/client";
import { like, save } from "@/lib/api/feed";
import { Link, useRouter } from "@/lib/i18n/navigation";

// Share and « more » sheets are downloaded when opened (ADR-004).
const ShareSheet = dynamic(() => import("./post-sheets").then((m) => m.ShareSheet));
const MoreSheet = dynamic(() => import("./post-sheets").then((m) => m.MoreSheet));

type Icons = Record<
  "heart" | "heartOn" | "comment" | "save" | "saveOn" | "share" | "more",
  ReactNode
>;

type Props = {
  postId: string;
  authorId: string;
  authorName: string;
  liked: boolean;
  saved: boolean;
  likeCount: number;
  commentCount: number;
  shareUrl: string;
  isMine: boolean;
  /** Drawn by the server: no icon code sent to the phone. */
  icons: Icons;
};

const buttonClass =
  "inline-flex min-h-12 min-w-12 items-center justify-center gap-1 rounded-full px-2 font-bold hover:bg-poudre";

/** Like, comment, save, share, more: big targets, an icon and a number or a word. */
export function PostActions(props: Props) {
  const t = useTranslations("social.post");
  const toast = useToast();
  const router = useRouter();
  const [liked, setLiked] = useState(props.liked);
  const [likes, setLikes] = useState(props.likeCount);
  const [saved, setSaved] = useState(props.saved);
  const [sheet, setSheet] = useState<"share" | "more" | null>(null);
  const [gone, setGone] = useState(false);

  const signedIn = () => {
    if (hasSession()) return true;
    router.push("/auth");
    return false;
  };

  const toggleLike = async () => {
    if (!signedIn()) return;
    const next = !liked;
    setLiked(next);
    setLikes((count) => count + (next ? 1 : -1));
    try {
      const counts = await like(props.postId, next);
      setLikes(counts.like_count);
      setLiked(counts.liked);
    } catch {
      setLiked(!next);
      setLikes((count) => count + (next ? -1 : 1));
    }
  };

  const toggleSave = async () => {
    if (!signedIn()) return;
    const next = !saved;
    setSaved(next);
    try {
      await save(props.postId, next);
      toast(next ? t("savedToast") : t("unsavedToast"), "success");
    } catch {
      setSaved(!next);
    }
  };

  if (gone) return <p className="text-prune-doux text-small">{t("hidden")}</p>;

  return (
    <div className="-mx-2 flex items-center justify-between">
      <div className="flex items-center">
        <button
          type="button"
          aria-pressed={liked}
          onClick={() => void toggleLike()}
          className={buttonClass}
          aria-label={liked ? t("unlike", { count: likes }) : t("like", { count: likes })}
        >
          {liked ? props.icons.heartOn : props.icons.heart}
          <span aria-hidden>{likes}</span>
        </button>
        <Link
          href={`/p/${props.postId}#comments`}
          className={buttonClass}
          aria-label={t("comments", { count: props.commentCount })}
        >
          {props.icons.comment}
          <span aria-hidden>{props.commentCount}</span>
        </Link>
        <button
          type="button"
          onClick={() => setSheet("share")}
          className={buttonClass}
          aria-label={t("share")}
        >
          {props.icons.share}
        </button>
      </div>
      <div className="flex items-center">
        <button
          type="button"
          aria-pressed={saved}
          onClick={() => void toggleSave()}
          className={buttonClass}
          aria-label={saved ? t("unsave") : t("save")}
        >
          {saved ? props.icons.saveOn : props.icons.save}
        </button>
        <button
          type="button"
          onClick={() => setSheet("more")}
          className={buttonClass}
          aria-label={t("more")}
        >
          {props.icons.more}
        </button>
      </div>
      {sheet === "share" && (
        <ShareSheet postId={props.postId} url={props.shareUrl} onClose={() => setSheet(null)} />
      )}
      {sheet === "more" && (
        <MoreSheet
          postId={props.postId}
          authorId={props.authorId}
          authorName={props.authorName}
          isMine={props.isMine}
          onClose={() => setSheet(null)}
          onGone={() => setGone(true)}
        />
      )}
    </div>
  );
}
