"use client";

import { useEffect, useSyncExternalStore } from "react";

/**
 * The space the person works in: her professional space or her client side. Shared screens (a
 * conversation, publishing, a call) send her back to the space she came from, never to the
 * other one. Kept for the tab only (sessionStorage).
 */
export type Space = "pro" | "client";

const KEY = "sg.space";

export const SPACE_HOME: Record<Space, string> = { pro: "/pro", client: "/" };
export const SPACE_MESSAGES: Record<Space, string> = { pro: "/pro/messages", client: "/messages" };

function read(): Space {
  try {
    return sessionStorage.getItem(KEY) === "pro" ? "pro" : "client";
  } catch {
    return "client";
  }
}

const noSubscription = () => () => undefined;

export function useSpace(): Space {
  return useSyncExternalStore(noSubscription, read, () => "client");
}

/** Placed in each shell: the space being shown becomes the one to come back to. */
export function SpaceMark({ space }: { space: Space }) {
  useEffect(() => {
    try {
      sessionStorage.setItem(KEY, space);
    } catch {
      // Private mode: the client side stays the default.
    }
  }, [space]);
  return null;
}
