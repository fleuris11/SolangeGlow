import type { Schemas } from "@/lib/api/client";

export type Media = Schemas["Media"];
type Variant = "thumb" | "medium" | "large";

/** Link of the best ready variant (in the order asked), or undefined. */
export function mediaSrc(media: Media | null | undefined, ...order: Variant[]): string | undefined {
  if (!media || media.status !== "ready") return undefined;
  const wanted = order.length ? order : (["medium", "large", "thumb"] as Variant[]);
  for (const name of wanted) {
    const url = media.urls[name] ?? media.urls[`poster_${name}`];
    if (url) return url;
  }
  return undefined;
}

/** Video link: low quality in data saver mode, medium otherwise. */
export function videoSrc(media: Media | null | undefined, dataSaver: boolean): string | undefined {
  if (!media || media.status !== "ready") return undefined;
  return (dataSaver ? media.urls.low : media.urls.medium) ?? media.urls.low ?? undefined;
}

export function voiceSrc(media: Media | null | undefined): string | undefined {
  if (!media || media.status !== "ready") return undefined;
  return media.urls.voice ?? undefined;
}
