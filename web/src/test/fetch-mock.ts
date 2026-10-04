import { vi } from "vitest";

type Route = {
  method?: string;
  path: string;
  status?: number;
  body?: unknown;
};

/**
 * Replaces fetch with fixed answers per "METHOD /api/v1/path".
 * Returns the mock to inspect calls.
 */
export function mockApi(routes: Route[]) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = (init?.method ?? "GET").toUpperCase();
    const route = routes.find(
      (r) => (r.method ?? "GET").toUpperCase() === method && url === `/api/v1${r.path}`,
    );
    if (!route) {
      return new Response(JSON.stringify({ code: "not_found" }), { status: 404 });
    }
    const status = route.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(route.body ?? {}), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Body sent with the n-th call to a path that carried one (POST, PATCH, DELETE). */
export function sentBody(fetchMock: ReturnType<typeof mockApi>, path: string, index = 0) {
  const calls = fetchMock.mock.calls.filter(
    ([url, init]) => url === `/api/v1${path}` && (init as RequestInit | undefined)?.body,
  );
  const init = calls[index]?.[1] as RequestInit | undefined;
  return init?.body ? JSON.parse(init.body as string) : undefined;
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
  avatar_url: null,
  has_password: false,
  onboarding_required: true,
  created_at: "2026-10-04T10:00:00Z",
};
