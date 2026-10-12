import {
  BookmarkSimple,
  CalendarCheck,
  ChatCircle,
  DotsThreeOutline,
  Heart,
  SealCheck,
  ShareNetwork,
} from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import { TradeLabel } from "@/components/features/trades/trade-label";
import { TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Avatar } from "@/components/ui/avatar";
import { buttonClasses } from "@/components/ui/button";
import type { Post } from "@/lib/api/social";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { PostActions } from "./post-actions";
import { timeAgo } from "./time-ago";

// Only posts with a video download the player.
const VideoPlayer = dynamic(() =>
  import("@/components/features/pros/showcase/video-player").then((m) => m.VideoPlayer),
);

const isTrade = (key: string): key is Trade => (TRADES as readonly string[]).includes(key);

function Picture({ src, alt, eager }: { src?: string; alt: string; eager?: boolean }) {
  if (!src) return <div className="bg-poudre aspect-[4/5] w-full" />;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- already resized by the backend
    <img
      src={src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      className="bg-poudre aspect-[4/5] w-full object-cover"
    />
  );
}

/** A post of the feed: who, the pictures, the words, « Book this look », and the actions. */
export function PostCard({ post, eager = false }: { post: Post; eager?: boolean }) {
  const t = useTranslations("social.post");
  const locale = useLocale();
  const author = post.author;
  const caption = post.caption || t("noCaption", { name: author.name });
  const items = post.media;
  const before = items.find((item) => item.role === "before");
  const after = items.find((item) => item.role === "after");
  const header = (
    <>
      <Avatar
        name={author.name}
        src={mediaSrc(author.photo, "thumb", "medium")}
        size="sm"
        halo={author.has_story}
      />
      <span className="flex min-w-0 flex-col">
        <span className="flex items-center gap-1 font-bold">
          <span className="truncate">{author.name}</span>
          {author.verified && (
            <SealCheck
              weight="fill"
              size={18}
              className="text-feuille shrink-0"
              aria-label={t("verified")}
            />
          )}
        </span>
        <span className="text-mention text-prune-doux">
          {[post.city, post.published_at ? timeAgo(post.published_at, locale) : null]
            .filter(Boolean)
            .join(", ")}
        </span>
      </span>
    </>
  );

  return (
    <article
      aria-labelledby={`post-${post.id}`}
      className="border-trait bg-carte rounded-card overflow-hidden border"
    >
      <header className="flex items-center gap-3 p-4">
        {author.pro_slug ? (
          <Link href={`/${author.pro_slug}`} className="flex min-w-0 flex-1 items-center gap-3">
            {header}
          </Link>
        ) : (
          <div className="flex min-w-0 flex-1 items-center gap-3">{header}</div>
        )}
      </header>

      {post.kind === "video" && items[0] ? (
        <VideoPlayer media={items[0].media} label={caption} />
      ) : post.kind === "before_after" && before && after ? (
        <div className="grid grid-cols-2 gap-1">
          {[
            [before, t("before")],
            [after, t("after")],
          ].map(([item, label]) => (
            <figure key={String(label)} className="relative">
              <Picture
                src={mediaSrc((item as typeof before).media, "medium", "large")}
                alt={t("beforeAfterAlt", { label: String(label), caption })}
                eager={eager}
              />
              <figcaption className="bg-carte text-mention absolute top-2 left-2 rounded-full px-2 py-1 font-bold">
                {String(label)}
              </figcaption>
            </figure>
          ))}
        </div>
      ) : items.length > 1 ? (
        <ul
          // Reachable with the keyboard: arrows scroll the pictures.
          tabIndex={0}
          aria-label={t("carousel", { count: items.length })}
          className="flex snap-x snap-mandatory [scrollbar-width:none] overflow-x-auto"
        >
          {items.map((item, index) => (
            <li key={item.media.id} className="w-full shrink-0 snap-start">
              <Picture
                src={mediaSrc(item.media, "medium", "large")}
                alt={t("carouselItem", { index: index + 1, count: items.length, caption })}
                eager={eager && index === 0}
              />
            </li>
          ))}
        </ul>
      ) : items[0] ? (
        <Picture src={mediaSrc(items[0].media, "medium", "large")} alt={caption} eager={eager} />
      ) : null}

      <div className="flex flex-col gap-3 p-4">
        <PostActions
          postId={post.id}
          authorId={author.id}
          authorName={author.name}
          liked={post.liked}
          saved={post.saved}
          likeCount={post.like_count}
          commentCount={post.comment_count}
          shareUrl={post.share_url}
          isMine={post.is_mine}
          icons={{
            heart: <Heart aria-hidden size={26} />,
            heartOn: <Heart aria-hidden size={26} weight="fill" className="text-hibiscus" />,
            comment: <ChatCircle aria-hidden size={26} />,
            save: <BookmarkSimple aria-hidden size={26} />,
            saveOn: <BookmarkSimple aria-hidden size={26} weight="fill" className="text-or" />,
            share: <ShareNetwork aria-hidden size={26} />,
            more: <DotsThreeOutline aria-hidden size={24} weight="fill" />,
          }}
        />
        <h2 id={`post-${post.id}`} className="sr-only">
          {t("by", { name: author.name })}
        </h2>
        {post.caption && <p className="whitespace-pre-line">{post.caption}</p>}
        {post.trade && isTrade(post.trade.key) && (
          <TradeLabel trade={post.trade.key} className="text-small text-prune-doux" />
        )}
        {post.service && author.pro_slug && (
          <Link href={`/${author.pro_slug}`} className={buttonClasses({ fullWidth: true })}>
            <CalendarCheck aria-hidden size={22} weight="bold" />
            {t("bookLook")}
          </Link>
        )}
      </div>
    </article>
  );
}
