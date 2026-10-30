import { Compass } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import { Fragment } from "react";

import { SponsoredPost } from "@/components/features/ads/ad-cards";
import { buttonClasses } from "@/components/ui/button";
import type { AdList } from "@/lib/api/ads";
import { EmptyState } from "@/components/ui/empty-state";
import type { Post } from "@/lib/api/social";
import { Link } from "@/lib/i18n/navigation";

import { FeedMore } from "./feed-more";
import { PostCard } from "./post-card";

type Props = {
  posts: Post[];
  next: string | null;
  title: string;
  source?: Parameters<typeof FeedMore>[0]["source"];
  /** Sponsored posts, one every `feed_every` posts (module 12). */
  sponsored?: AdList | null;
};

/** A list of posts rendered on the server, with « See more » for the next pages. */
export function FeedSection({
  posts,
  next,
  title,
  source = { kind: "feed" },
  sponsored = null,
}: Props) {
  const t = useTranslations("social.feed");
  return (
    <section aria-labelledby="feed-title" className="flex flex-col gap-4">
      <h2 id="feed-title" className="text-title font-bold">
        {title}
      </h2>
      {posts.length === 0 ? (
        <EmptyState
          icon={<Compass size={48} weight="duotone" />}
          title={t("emptyTitle")}
          description={t("emptyText")}
          action={
            <Link href="/explore" className={buttonClasses({ size: "lg" })}>
              {t("emptyCta")}
            </Link>
          }
        />
      ) : (
        <ul className="flex flex-col gap-6">
          {posts.map((post, index) => {
            const every = sponsored?.feed_every ?? 0;
            const ad =
              every && (index + 1) % every === 0
                ? sponsored?.results[(index + 1) / every - 1]
                : undefined;
            return (
              <Fragment key={post.id}>
                <li>
                  <PostCard post={post} eager={index === 0} />
                </li>
                {ad && (
                  <li>
                    <SponsoredPost ad={ad} />
                  </li>
                )}
              </Fragment>
            );
          })}
          <FeedMore source={source} next={next} />
        </ul>
      )}
    </section>
  );
}
