"use client";

import type { ReactNode } from "react";

import { Link } from "@/lib/i18n/navigation";
import { SPACE_HOME, useSpace } from "@/lib/navigation/space";

/** The way back of a focused screen: home of the space she came from (activity or client side). */
export function SpaceBack({
  label,
  icon,
  className,
}: {
  label: string;
  /** Drawn by the server (ADR-004). */
  icon: ReactNode;
  className?: string;
}) {
  const space = useSpace();
  return (
    <Link href={SPACE_HOME[space]} aria-label={label} className={className}>
      {icon}
    </Link>
  );
}
