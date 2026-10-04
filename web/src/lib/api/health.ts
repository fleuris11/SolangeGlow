import { apiFetch } from "./client";

export type Health = { status: "ok" };

export const healthQueryKey = ["health"] as const;

export function getHealth(): Promise<Health> {
  return apiFetch<Health>("/health");
}
