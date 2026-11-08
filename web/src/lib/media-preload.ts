import { preload } from "react-dom";

import { mediaSrc, mediaSrcSet, type Media } from "./media";

/**
 * The main picture of a page (showcase, product, course) asked for in the <head>, at the same time
 * as the styles, instead of when the browser reaches its <img>. Server components only.
 */
export function preloadMainPicture(media: Media | null | undefined, sizes: string) {
  const src = mediaSrc(media, "large", "medium");
  if (!src) return;
  const imageSrcSet = mediaSrcSet(media);
  preload(src, {
    as: "image",
    fetchPriority: "high",
    imageSrcSet,
    imageSizes: imageSrcSet ? sizes : undefined,
  });
}
