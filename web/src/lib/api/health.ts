import { api, unwrap } from "./client";

export const healthQueryKey = ["health"] as const;

export const getHealth = () => unwrap(api.GET("/api/v1/health"));
