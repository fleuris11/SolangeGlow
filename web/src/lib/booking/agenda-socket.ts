/**
 * The agenda's WebSocket (loaded on demand): « something changed », the agenda reads its
 * days again. Same cookie as the API; reconnects with a growing delay.
 */
function socketUrl(proId?: string): string {
  const configured = process.env.NEXT_PUBLIC_WS_ORIGIN;
  const { protocol, hostname, port, host } = window.location;
  const scheme = protocol === "https:" ? "wss:" : "ws:";
  const origin =
    configured || (port === "3000" ? `${scheme}//${hostname}:8000` : `${scheme}//${host}`);
  return `${origin}/ws/agenda/${proId ? `?pro=${encodeURIComponent(proId)}` : ""}`;
}

export function connectAgenda(onChange: () => void, proId?: string): () => void {
  let socket: WebSocket | null = null;
  let stopped = false;
  let delay = 2_000;
  let timer: number | undefined;
  let ping: number | undefined;

  const open = () => {
    socket = new WebSocket(socketUrl(proId));
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { type?: string };
        if (data.type === "agenda.changed") onChange();
      } catch {
        // Ignore anything that is not ours.
      }
    };
    socket.onopen = () => {
      delay = 2_000;
      ping = window.setInterval(() => socket?.send(JSON.stringify({ type: "ping" })), 30_000);
    };
    socket.onclose = (event) => {
      window.clearInterval(ping);
      // 4401 = not signed in, 4404 = no agenda: no point in retrying.
      if (stopped || event.code === 4401 || event.code === 4404) return;
      timer = window.setTimeout(open, delay);
      delay = Math.min(delay * 2, 60_000);
      onChange(); // what happened meanwhile
    };
  };

  open();
  return () => {
    stopped = true;
    window.clearTimeout(timer);
    window.clearInterval(ping);
    socket?.close();
  };
}
