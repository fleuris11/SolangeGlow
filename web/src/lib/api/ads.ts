/** Ads (module 12): the ads of a placement (already counted as shown), the boosts of a pro. */
import { api, unwrap, type Schemas } from "./client";

export type Ad = Schemas["Ad"];
export type AdList = Schemas["AdList"];
export type AdPlacement = Schemas["AdPlacementEnum"];
export type BoostPage = Schemas["BoostPage"];
export type BoostDuration = Schemas["BoostDurationEnum"];

export type AdQuery = { placement: AdPlacement; count?: number; city?: string; trade?: string };

export const getAds = (query: AdQuery) => unwrap(api.GET("/api/v1/ads", { params: { query } }));
export const getBoosts = () => unwrap(api.GET("/api/v1/ads/boosts"));
export const buyBoost = (duration: BoostDuration) =>
  unwrap(api.POST("/api/v1/ads/boosts", { body: { duration } }));
