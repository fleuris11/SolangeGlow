/** Accounts and sign-in, on top of the generated client (types follow the backend). */
import { api, ApiError, hasSession, unwrap, type Schemas } from "./client";

export type Me = Schemas["Me"];
export type Media = Schemas["Media"];
export type CodeRequest = Schemas["CodeRequestResult"];
export type SignIn = Schemas["SignIn"];
export type Trade = Schemas["Trade"];
export type Country = Schemas["Country"];
export type Guest = Schemas["Guest"];
export type MePatch = Schemas["PatchedMeRequest"];

export const meQueryKey = ["me"] as const;

/** The signed-in person, or null for a visitor. */
export async function getMe(): Promise<Me | null> {
  if (!hasSession()) return null;
  try {
    return await unwrap(api.GET("/api/v1/me"));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
    throw error;
  }
}

export const requestCode = (body: Schemas["CodeRequestRequest"]) =>
  unwrap(api.POST("/api/v1/auth/otp/request", { body }));

export const verifyCode = (body: Schemas["CodeVerifyRequest"]) =>
  unwrap(api.POST("/api/v1/auth/otp/verify", { body }));

export const loginWithPassword = (body: Schemas["PasswordLoginRequest"]) =>
  unwrap(api.POST("/api/v1/auth/password/login", { body }));

export const logout = () => unwrap(api.POST("/api/v1/auth/logout"));
export const logoutEverywhere = () => unwrap(api.POST("/api/v1/auth/logout-all"));

export const updateMe = (body: MePatch) => unwrap(api.PATCH("/api/v1/me", { body }));

/** Asks for deletion: erased after the grace period unless she signs in again. */
export const deleteAccount = () =>
  // The schema leaves out bodies of DELETE requests; the backend still requires this one.
  unwrap(api.DELETE("/api/v1/me", { body: { confirm: true } } as never)) as Promise<
    Schemas["DeletionScheduled"]
  >;

export function uploadPhoto(file: File) {
  const form = new FormData();
  form.append("photo", file);
  return unwrap(api.POST("/api/v1/me/photo", { body: form as unknown as Schemas["PhotoRequest"] }));
}

export const removePhoto = () => unwrap(api.DELETE("/api/v1/me/photo"));

export const setPassword = (password: string) =>
  unwrap(api.POST("/api/v1/me/password", { body: { password } }));

export const completeOnboarding = (body: Schemas["OnboardingRequest"]) =>
  unwrap(api.POST("/api/v1/me/onboarding", { body }));

export const requestContactChange = (body: Schemas["ContactChangeRequestRequest"]) =>
  unwrap(api.POST("/api/v1/me/contact", { body }));

export const confirmContactChange = (body: Schemas["ContactChangeConfirmRequest"]) =>
  unwrap(api.POST("/api/v1/me/contact/confirm", { body }));

export async function getGuest(): Promise<Guest | null> {
  try {
    return await unwrap(api.GET("/api/v1/guest"));
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export const createGuest = (body: Schemas["GuestRequest"]) =>
  unwrap(api.POST("/api/v1/guest", { body }));

export const getTrades = () => unwrap(api.GET("/api/v1/trades"));
export const getCountries = () => unwrap(api.GET("/api/v1/countries"));
