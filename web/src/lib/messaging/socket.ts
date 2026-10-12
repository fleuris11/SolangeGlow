/**
 * The messaging WebSocket of this tab (one for every screen): reconnects with a growing
 * delay, says "I am here" every 30 s, confirms received messages, renews the session when
 * the access cookie expired. Messages themselves are sent through the API (ADR-006).
 */
import { CLIENT_HEADER } from "@/lib/api/client";

import { emit, setSender, type MessagingEvent, type OutgoingEvent } from "./bus";

let started = false;
let viewing: string | null = null;

function socketUrl(): string {
  const configured = process.env.NEXT_PUBLIC_WS_ORIGIN;
  const { protocol, hostname, port, host } = window.location;
  const scheme = protocol === "https:" ? "wss:" : "ws:";
  const origin =
    configured || (port === "3000" ? `${scheme}//${hostname}:8000` : `${scheme}//${host}`);
  return `${origin}/ws/messaging/`;
}

async function renewSession(): Promise<boolean> {
  try {
    const response = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "same-origin",
      headers: { ...CLIENT_HEADER },
    });
    return response.ok;
  } catch {
    return false;
  }
}

/** Starts once per tab; later calls do nothing. */
export function startSocket(): void {
  if (started || typeof window === "undefined" || typeof WebSocket === "undefined") return;
  started = true;
  let socket: WebSocket | null = null;
  let delay = 2_000;
  let retry: number | undefined;
  let ping: number | undefined;
  let renewed = false;

  const sendRaw = (event: OutgoingEvent): boolean => {
    if (event.type === "viewing") viewing = event.conversation;
    if (socket?.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(event));
    return true;
  };
  setSender(sendRaw);

  const schedule = () => {
    window.clearTimeout(retry);
    retry = window.setTimeout(open, delay);
    delay = Math.min(delay * 2, 60_000);
  };

  const open = () => {
    try {
      socket = new WebSocket(socketUrl());
    } catch {
      schedule();
      return;
    }
    socket.onopen = () => {
      delay = 2_000;
      renewed = false;
      emit({ type: "connected" });
      sendRaw({ type: "delivered" });
      if (viewing) sendRaw({ type: "viewing", conversation: viewing });
      window.clearInterval(ping);
      ping = window.setInterval(() => socket?.send(JSON.stringify({ type: "ping" })), 30_000);
    };
    socket.onmessage = (raw) => {
      let event: MessagingEvent;
      try {
        event = JSON.parse(raw.data as string) as MessagingEvent;
      } catch {
        return;
      }
      // Her device got it: « received » for the sender.
      if (event.type === "message") sendRaw({ type: "delivered" });
      emit(event);
    };
    socket.onclose = (event) => {
      window.clearInterval(ping);
      emit({ type: "disconnected" });
      if (event.code === 4401) {
        // Access cookie expired: renew once, then try again.
        if (renewed) return;
        renewed = true;
        void renewSession().then((ok) => ok && schedule());
        return;
      }
      schedule();
    };
  };

  // Back online or back on the tab: reconnect at once instead of waiting.
  const wake = () => {
    if (socket && socket.readyState <= WebSocket.OPEN) return;
    delay = 2_000;
    window.clearTimeout(retry);
    open();
  };
  window.addEventListener("online", wake);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") wake();
  });

  open();
}
