/**
 * Messages written without network wait here (in this browser) and leave as soon as the
 * connection comes back. Each one keeps its client_id: sending twice never makes two
 * messages (ADR-006).
 */
import type { MessageInput } from "@/lib/api/messaging";

export type Pending = {
  clientId: string;
  conversationId: string;
  body: MessageInput;
  createdAt: string;
  failed?: boolean;
};

const KEY = "sg.outbox";
const listeners = new Set<() => void>();

function read(): Pending[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Pending[]) : [];
  } catch {
    return [];
  }
}

function write(items: Pending[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    // Private window or full storage: the message stays only on screen.
  }
  for (const listener of listeners) listener();
}

export function newClientId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  // Old browsers: a random version-4 UUID.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0;
    return (char === "x" ? random : (random & 0x3) | 0x8).toString(16);
  });
}

export function add(item: Pending): void {
  write([...read().filter((p) => p.clientId !== item.clientId), item]);
}

export function remove(clientId: string): void {
  write(read().filter((p) => p.clientId !== clientId));
}

export function markFailed(clientId: string): void {
  write(read().map((p) => (p.clientId === clientId ? { ...p, failed: true } : p)));
}

export function pendingFor(conversationId: string): Pending[] {
  return read().filter((p) => p.conversationId === conversationId);
}

export function onChange(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

let flushing = false;

/**
 * Sends what waits, oldest first. A refusal of the server (4xx) marks the message as
 * failed (shown with « Try again »); a network error stops and waits for the next try.
 */
export async function flush(
  sendOne: (item: Pending) => Promise<unknown>,
  isRefusal: (error: unknown) => boolean,
): Promise<void> {
  if (flushing) return;
  flushing = true;
  try {
    for (const item of read().filter((p) => !p.failed)) {
      try {
        await sendOne(item);
        remove(item.clientId);
      } catch (error) {
        if (isRefusal(error)) markFailed(item.clientId);
        else break;
      }
    }
  } finally {
    flushing = false;
  }
}
