import type { TextSize, Theme } from "@/lib/preferences/preferences";

import { ApiError, apiFetch, hasSession } from "./client";

export type Me = {
  id: string;
  phone: string | null;
  email: string | null;
  first_name: string;
  last_name: string;
  city: string;
  country: string | null;
  preferred_language: "fr" | "en" | "sk";
  preferred_currency: string | null;
  theme: Theme;
  text_size: TextSize;
  data_saver: boolean;
  audio_mode: boolean;
  notify_whatsapp: boolean;
  notify_email: boolean;
  notify_push: boolean;
  roles: string[];
  is_pro: boolean;
  avatar_url: string | null;
  has_password: boolean;
  onboarding_required: boolean;
  created_at: string;
};

export type CodeRequest = {
  challenge_id: string;
  channel: "whatsapp" | "sms" | "email" | "console";
  resend_after: number;
  expires_in: number;
};

export type SignIn = { created: boolean; user: Me };
export type Trade = { key: string; name: string; icon: string };
export type Country = {
  code: string;
  name: string;
  phone_prefix: string;
  default_currency: string;
};
export type Guest = { id: string; first_name: string; phone: string };

export const meQueryKey = ["me"] as const;

/** The signed-in person, or null for a visitor. */
export async function getMe(): Promise<Me | null> {
  if (!hasSession()) return null;
  try {
    return await apiFetch<Me>("/me");
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
    throw error;
  }
}

export const requestCode = (body: { phone?: string; email?: string; locale?: string }) =>
  apiFetch<CodeRequest>("/auth/otp/request", { method: "POST", body });

export const verifyCode = (body: { challenge_id: string; code: string; locale?: string }) =>
  apiFetch<SignIn>("/auth/otp/verify", { method: "POST", body });

export const loginWithPassword = (body: { identifier: string; password: string }) =>
  apiFetch<SignIn>("/auth/password/login", { method: "POST", body });

export const logout = () => apiFetch<{ status: string }>("/auth/logout", { method: "POST" });

export const logoutEverywhere = () =>
  apiFetch<{ status: string }>("/auth/logout-all", { method: "POST" });

export const updateMe = (body: Partial<Me>) => apiFetch<Me>("/me", { method: "PATCH", body });

export const deleteAccount = () =>
  apiFetch<void>("/me", { method: "DELETE", body: { confirm: true } });

export function uploadAvatar(file: File) {
  const form = new FormData();
  form.append("photo", file);
  return apiFetch<Me>("/me/avatar", { method: "POST", body: form });
}

export const removeAvatar = () => apiFetch<Me>("/me/avatar", { method: "DELETE" });

export const setPassword = (password: string) =>
  apiFetch<{ status: string }>("/me/password", { method: "POST", body: { password } });

export const completeOnboarding = (body: {
  mode: "client" | "pro";
  trades?: string[];
  language?: string;
  city?: string;
}) => apiFetch<Me>("/me/onboarding", { method: "POST", body });

export async function getGuest(): Promise<Guest | null> {
  try {
    return await apiFetch<Guest>("/guest");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export const createGuest = (body: { first_name: string; phone: string }) =>
  apiFetch<Guest>("/guest", { method: "POST", body });

export const getTrades = () => apiFetch<Trade[]>("/trades");
export const getCountries = () => apiFetch<Country[]>("/countries");
