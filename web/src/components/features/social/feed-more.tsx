"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { getFeed, getPersonPosts, getSaved } from "@/lib/api/feed";
import type { Post } from "@/lib/api/social";

// The first page comes from the server; this code is only for the next ones.
const PostCard = dynamic(() => import("./post-card").then((m) => m.PostCard));

type Source =
  { kind: "feed"; city?: string } | { kind: "person"; userId: string } | { kind: "saved" };

/** « See more posts »: the next pages of the feed (cursor), added under the first one. */
export function FeedMore({ source, next }: { source: Source; next: string | null }) {
  const t = useTranslations("social.feed");
  const [posts, setPosts] = useState<Post[]>([]);
  const [cursor, setCursor] = useState(next);
  const [busy, setBusy] = useState(false);

  const more = async () => {
    if (!cursor) return;
    setBusy(true);
    try {
      const page =
        source.kind === "feed"
          ? await getFeed({ cursor, city: source.city })
          : source.kind === "person"
            ? await getPersonPosts(source.userId, cursor)
            : await getSaved(cursor);
      setPosts((current) => [...current, ...page.results]);
      setCursor(page.next ?? null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {posts.map((post) => (
        <li key={post.id}>
          <PostCard post={post} />
        </li>
      ))}
      {cursor && (
        <li>
          <Button variant="secondary" fullWidth disabled={busy} onClick={() => void more()}>
            {t("more")}
          </Button>
        </li>
      )}
    </>
  );
}
