import type { ReactNode } from "react";

/** One column: choosing and paying read better narrow, even on a large screen. */
export default function Layout({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-[640px]">{children}</div>;
}
