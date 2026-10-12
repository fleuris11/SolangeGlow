"use client";

import { BookmarkSimple, Rocket, Trash } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { deletePost, getMyPosts, getSaved, updatePost } from "@/lib/api/social";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { PostCard } from "./post-card";

const TABS = ["draft", "scheduled", "published"] as const;

/** Her drafts, scheduled and published posts: publish a draft, delete. */
export function MyPosts() {
  const t = useTranslations("social.myPosts");
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<(typeof TABS)[number]>("draft");
  const query = useQuery({ queryKey: ["my-posts", tab], queryFn: () => getMyPosts(tab) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["my-posts"] });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("tabs")}>
        {TABS.map((value) => (
          <Chip key={value} selected={tab === value} onClick={() => setTab(value)}>
            {t(`tab.${value}`)}
          </Chip>
        ))}
      </div>
      {query.isPending ? (
        <Skeleton className="rounded-card h-48" />
      ) : query.data?.results.length ? (
        <ul className="flex flex-col gap-3">
          {query.data.results.map((post) => (
            <li
              key={post.id}
              className="border-trait bg-carte rounded-card flex items-center gap-3 border p-3"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
              <img
                src={mediaSrc(post.media[0]?.media, "thumb")}
                alt=""
                className="bg-poudre size-16 shrink-0 rounded-2xl object-cover"
              />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate">{post.caption || t("noCaption")}</span>
                {post.publish_at && (
                  <span className="text-small text-prune-doux">
                    {t("on", {
                      date: new Intl.DateTimeFormat(locale, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }).format(new Date(post.publish_at)),
                    })}
                  </span>
                )}
                {post.visibility !== "visible" && (
                  <span className="text-small text-alerte font-bold">{t("inReview")}</span>
                )}
              </span>
              {post.status === "published" ? (
                <Link href={`/p/${post.id}`} className={buttonClasses({ variant: "quiet" })}>
                  {t("see")}
                </Link>
              ) : (
                <Button
                  variant="secondary"
                  onClick={async () => {
                    await updatePost(post.id, { status: "published" });
                    await refresh();
                  }}
                >
                  <Rocket aria-hidden size={20} />
                  {t("publish")}
                </Button>
              )}
              <Button
                variant="quiet"
                aria-label={t("delete")}
                onClick={async () => {
                  await deletePost(post.id);
                  await refresh();
                }}
              >
                <Trash aria-hidden size={20} />
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-prune-doux">{t(`empty.${tab}`)}</p>
      )}
    </div>
  );
}

/** Posts she saved, newest first. */
export function SavedPosts() {
  const t = useTranslations("social.saved");
  const query = useQuery({ queryKey: ["saved"], queryFn: () => getSaved() });
  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const posts = query.data?.results ?? [];
  if (!posts.length) {
    return (
      <EmptyState
        icon={<BookmarkSimple size={48} weight="duotone" />}
        title={t("emptyTitle")}
        description={t("emptyText")}
        action={
          <Link href="/" className={buttonClasses({ size: "lg" })}>
            {t("emptyCta")}
          </Link>
        }
      />
    );
  }
  return (
    <ul className="flex flex-col gap-6">
      {posts.map((post) => (
        <li key={post.id}>
          <PostCard post={post} />
        </li>
      ))}
    </ul>
  );
}
