/**
 * Single entry point for calls to the Django API.
 * The browser calls /api/* on the web origin; Next.js forwards it to the backend.
 * Typed endpoints will be generated from /api/schema/ (openapi-typescript).
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(`API error ${status}${code ? ` (${code})` : ""}`);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers: { Accept: "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { code?: string } | null;
    throw new ApiError(response.status, body?.code);
  }
  return (await response.json()) as T;
}
