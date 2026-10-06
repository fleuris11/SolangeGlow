/**
 * WebSocket to the backend (Django Channels), signed in by the same httpOnly cookie.
 * In local development the site runs on :3000 and the backend on :8000; in production
 * both share the domain and /ws/ is forwarded by the reverse proxy.
 */
export type UnreadMessage = {
  type: "unread";
  unread: number;
  notification?: { id: string; title: string; body: string } | null;
};

function socketUrl(): string {
  const configured = process.env.NEXT_PUBLIC_WS_ORIGIN;
  const { protocol, hostname, port, host } = window.location;
  const scheme = protocol === "https:" ? "wss:" : "ws:";
  const origin =
    configured || (port === "3000" ? `${scheme}//${hostname}:8000` : `${scheme}//${host}`);
  return `${origin}/ws/notifications/`;
}

/** Connects and reconnects (with a growing delay) until `stop` is called. */
export function connect(onMessage: (message: UnreadMessage) => void): () => void {
  let socket: WebSocket | null = null;
  let stopped = false;
  let delay = 2_000;
  let timer: number | undefined;

  const open = () => {
    socket = new WebSocket(socketUrl());
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as UnreadMessage;
        if (data.type === "unread") onMessage(data);
      } catch {
        // Ignore anything that is not ours.
      }
    };
    socket.onopen = () => {
      delay = 2_000;
    };
    socket.onclose = (event) => {
      // 4401 = not signed in: no point in retrying.
      if (stopped || event.code === 4401) return;
      timer = window.setTimeout(open, delay);
      delay = Math.min(delay * 2, 60_000);
    };
  };

  open();
  return () => {
    stopped = true;
    window.clearTimeout(timer);
    socket?.close();
  };
}
