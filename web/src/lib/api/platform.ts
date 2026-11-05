import { api, unwrap } from "./client";

export const platformQueryKey = ["platform"] as const;

/** What the screens need to know before showing a way to pay (the owner opens it in the admin). */
export const getPlatform = () => unwrap(api.GET("/api/v1/platform"));
