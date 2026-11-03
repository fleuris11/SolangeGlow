import Image from "next/image";

import { cn } from "@/lib/cn";

type Props = {
  src: string;
  alt: string;
  sizes?: string;
  className?: string;
};

/**
 * A photo that drifts slightly slower than the page. CSS scroll timeline only, no script:
 * without browser support or with reduced animations, the photo simply stays still.
 */
export function ParallaxImage({ src, alt, sizes = "100vw", className }: Props) {
  return (
    <div className={cn("relative overflow-hidden", className)}>
      <Image src={src} alt={alt} fill sizes={sizes} className="sg-parallax object-cover" />
    </div>
  );
}
