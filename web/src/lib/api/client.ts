/**
 * Single entry point for calls to the Django API.
 * The browser calls /api/* on the web origin; Next.js forwards it to the backend.
 * Sign-in tokens live in httpOnly cookies: this code never reads them.
 */
export type ApiErrorBody = {
  code?: string;
  message?: string;
  fields?: Record<string, string[] | string>;
  attempts_left?: number;
  retry_after?: number;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string = "error",
    public readonly body: ApiErrorBody = {},
  ) {
    super(body.message || `API error ${status} (${code})`);
    this.name = "ApiError";
  }

  /** First message of a field error, or the general message. */
  fieldMessage(field: string): string | undefined {
    const value = this.body.fields?.[field];
    return Array.isArray(value) ? value[0] : value;
  }
}

/** Sent on every call: lets the backend refuse cross-site requests made with our cookies. */
export const CLIENT_HEADER = { "X-SG-Client": "web" } as const;

type Options = Omit<RequestInit, "body"> & {
  /** Plain object sent as JSON, or FormData for uploads. */
  body?: unknown;
  /** Internal: avoid refreshing the session twice. */
  retried?: boolean;
};

function currentLocale(): string {
  return typeof document === "undefined" ? "fr" : document.documentElement.lang || "fr";
}

/** True when a session cookie exists (set by the backend, holds no secret). */
export function hasSession(): boolean {
  return typeof document !== "undefined" && /(?:^|;\s*)sg_signed_in=1/.test(document.cookie);
}

let refreshing: Promise<boolean> | null = null;

/** Renews the session cookies once, shared by every call that needs it. */
function refreshSession(): Promise<boolean> {
  refreshing ??= fetch("/api/v1/auth/refresh", {
    method: "POST",
    credentials: "same-origin",
    headers: { ...CLIENT_HEADER },
  })
    .then((response) => response.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function apiFetch<T>(path: string, options: Options = {}): Promise<T> {
  const { body, retried, headers, ...init } = options;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Accept-Language": currentLocale(),
      ...CLIENT_HEADER,
      ...(body !== undefined && !isForm ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  });

  if (response.status === 401 && !retried && !path.startsWith("/auth/") && hasSession()) {
    if (await refreshSession()) {
      return apiFetch<T>(path, { ...options, retried: true });
    }
  }

  if (!response.ok) {
    const errorBody = ((await response.json().catch(() => null)) ?? {}) as ApiErrorBody;
    throw new ApiError(response.status, errorBody.code, errorBody);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
