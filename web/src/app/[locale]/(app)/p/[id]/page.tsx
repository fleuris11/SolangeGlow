import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { cache } from "react";

import { LazyComments } from "@/components/features/social/lazy";
import { PostCard } from "@/components/features/social/post-card";
import { postOnServer, SITE_URL } from "@/lib/api/server";
import type { Locale } from "@/lib/i18n/routing";
import { mediaSrc } from "@/lib/media";

type Props = { params: Promise<{ locale: Locale; id: string }> };

const loadPost = cache((id: string, locale: string) =>
  /^[0-9a-f-]{36}$/i.test(id) ? postOnServer(id, locale) : null,
);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, id } = await params;
  const post = await loadPost(id, locale);
  if (!post) return {};
  const t = await getTranslations({ locale, namespace: "social.post" });
  const first = post.media.find((item) => item.role !== "before") ?? post.media[0];
  const image = mediaSrc(first?.media, "large", "medium");
  const title = t("metaTitle", { name: post.author.name });
  const description =
    post.caption.slice(0, 160) || t("metaDescription", { name: post.author.name });
  const url = `${SITE_URL}/${locale}/p/${post.id}`;
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      title,
      description,
      url,
      ...(image
        ? { images: [{ url: image.startsWith("http") ? image : `${SITE_URL}${image}` }] }
        : {}),
    },
    twitter: { card: image ? "summary_large_image" : "summary" },
  };
}

export default async function PostPage({ params }: Props) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  const post = await loadPost(id, locale);
  if (!post) notFound();
  return (
    <div className="flex flex-col gap-8">
      <PostCard post={post} eager />
      <LazyComments postId={post.id} />
    </div>
  );
}
