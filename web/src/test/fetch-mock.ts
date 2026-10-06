import { vi } from "vitest";

type Route = {
  method?: string;
  path: string;
  status?: number;
  body?: unknown;
};

export type Recorded = { path: string; method: string; body: unknown };

/**
 * Replaces fetch with fixed answers per "METHOD /api/v1/path".
 * Accepts URLs and Request objects (the generated client sends Requests).
 * Every call is recorded in `fetchMock.records`.
 */
export function mockApi(routes: Route[]) {
  const records: Recorded[] = [];
  const fetchMock = Object.assign(
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request =
        input instanceof Request
          ? input
          : new Request(new URL(String(input), "http://localhost:3000"), init);
      const { pathname } = new URL(request.url);
      const method = request.method.toUpperCase();
      const text = await request.clone().text();
      let body: unknown;
      try {
        body = text ? JSON.parse(text) : undefined;
      } catch {
        body = text;
      }
      records.push({ path: pathname, method, body });

      const route = routes.find(
        (r) => (r.method ?? "GET").toUpperCase() === method && pathname === `/api/v1${r.path}`,
      );
      if (!route) {
        return new Response(JSON.stringify({ code: "not_found" }), { status: 404 });
      }
      const status = route.status ?? 200;
      return new Response(status === 204 ? null : JSON.stringify(route.body ?? {}), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    }),
    { records },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Body sent with the n-th call to a path that carried one (POST, PATCH, DELETE). */
export function sentBody(fetchMock: ReturnType<typeof mockApi>, path: string, index = 0) {
  return fetchMock.records.filter((r) => r.path === `/api/v1${path}` && r.body !== undefined)[index]
    ?.body as Record<string, unknown> | undefined;
}

/** True when the path was called (optionally with this method). */
export function called(fetchMock: ReturnType<typeof mockApi>, path: string, method?: string) {
  return fetchMock.records.some(
    (r) => r.path === `/api/v1${path}` && (!method || r.method === method),
  );
}

export const ME = {
  id: "u1",
  phone: "+2290197123456",
  email: null,
  first_name: "",
  last_name: "",
  city: "",
  country: "BJ",
  preferred_language: "fr",
  preferred_currency: "XOF",
  theme: "system",
  text_size: "normal",
  data_saver: false,
  audio_mode: false,
  notify_whatsapp: true,
  notify_email: true,
  notify_push: true,
  roles: ["client"],
  is_pro: false,
  photo: null,
  birth_date: "1995-04-12",
  is_minor: false,
  quiet_hours_start: null,
  quiet_hours_end: null,
  has_password: false,
  onboarding_required: true,
  created_at: "2026-10-04T10:00:00Z",
};
