/**
 * Live events of the messaging, shared by every screen of the tab. The socket itself is
 * downloaded only for signed-in people (`./socket`, ADR-004); this file stays tiny.
 */
import type { Message } from "@/lib/api/messaging";

/** A call changed (rings, answered, over): screens read it again. */
export type CallEvent = {
  id: string;
  kind: "audio" | "video";
  status: string;
  caller_id: string | null;
  conversation_id: string;
};

export type MessagingEvent =
  | { type: "hello"; count: number; requests: number }
  | { type: "unread"; count: number; requests: number }
  | { type: "message"; message: Message }
  | {
      type: "receipt";
      conversation: string;
      user: string;
      delivered_up_to: string | null;
      read_up_to: string | null;
    }
  | { type: "typing"; conversation: string; user: string }
  | { type: "presence"; user: string; online: boolean; last_seen: string | null }
  | { type: "conversation"; conversation: string; status: string }
  | { type: "call_incoming" | "call"; call: CallEvent }
  | { type: "connected" }
  | { type: "disconnected" };

export type OutgoingEvent =
  | { type: "typing"; conversation: string }
  | { type: "read"; conversation: string }
  | { type: "viewing"; conversation: string | null }
  | { type: "delivered" };

type Listener = (event: MessagingEvent) => void;

const listeners = new Set<Listener>();
let sender: ((event: OutgoingEvent) => boolean) | null = null;
let connected = false;

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function emit(event: MessagingEvent): void {
  if (event.type === "connected") connected = true;
  if (event.type === "disconnected") connected = false;
  for (const listener of listeners) listener(event);
}

/** Sends through the socket when it is open; returns false otherwise. */
export function send(event: OutgoingEvent): boolean {
  return sender ? sender(event) : false;
}

export function setSender(fn: ((event: OutgoingEvent) => boolean) | null): void {
  sender = fn;
}

export function isConnected(): boolean {
  return connected;
}
