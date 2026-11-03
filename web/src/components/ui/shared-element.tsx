import * as React from "react";
import type { ComponentType, ReactNode } from "react";

type TransitionProps = { name: string; children: ReactNode };

// Only in the React build that Next ships, not in its types.
const ViewTransition = (React as unknown as { ViewTransition?: ComponentType<TransitionProps> })
  .ViewTransition;

/**
 * The same photo on two pages, with the same name: the card grows into the page header
 * (signature moment 2). Browsers without View Transitions simply change page.
 */
export function SharedElement({ name, children }: TransitionProps) {
  if (!ViewTransition) return <>{children}</>;
  return <ViewTransition name={name}>{children}</ViewTransition>;
}
