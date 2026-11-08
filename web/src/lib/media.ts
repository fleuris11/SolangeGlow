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

/** "medium 640w, large 1280w": a phone takes the smaller picture, a computer the larger. */
export function mediaSrcSet(media: Media | null | undefined): string | undefined {
  if (!media || media.status !== "ready") return undefined;
  const parts = (
    [
      ["medium", 640],
      ["large", 1280],
    ] as const
  )
    .filter(([name]) => media.urls[name])
    .map(([name, width]) => `${media.urls[name]} ${width}w`);
  return parts.length > 1 ? parts.join(", ") : undefined;
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
