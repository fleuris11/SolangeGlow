/** Lives (training and sales): the room, questions, raised hands, sales of the shop. */
import { api, unwrap, type Schemas } from "./client";

export type LiveKind = "training" | "sale";
export type LiveState = Schemas["LiveState"];
export type LiveJoin = Schemas["LiveJoin"];
export type LivePin = Schemas["LivePin"];
export type LiveQuestion = Schemas["LiveQuestion"];
export type UpcomingLive = Schemas["UpcomingLive"];
export type MySaleLives = Schemas["MySaleLives"];
export type MySaleLive = Schemas["MySaleLive"];

const room = (kind: LiveKind, id: string) => ({ params: { path: { kind, source_id: id } } });

export const getLive = (kind: LiveKind, id: string) =>
  unwrap(api.GET("/api/v1/live/{kind}/{source_id}", room(kind, id)));
export const joinLive = (kind: LiveKind, id: string) =>
  unwrap(api.POST("/api/v1/live/{kind}/{source_id}/join", room(kind, id)));
export const startLive = (kind: LiveKind, id: string) =>
  unwrap(api.POST("/api/v1/live/{kind}/{source_id}/start", room(kind, id)));
export const endLive = (kind: LiveKind, id: string) =>
  unwrap(api.POST("/api/v1/live/{kind}/{source_id}/end", room(kind, id)));
export const askQuestion = (kind: LiveKind, id: string, text: string) =>
  unwrap(
    api.POST("/api/v1/live/{kind}/{source_id}/questions", { ...room(kind, id), body: { text } }),
  );
export const markAnswered = (kind: LiveKind, id: string, questionId: string) =>
  unwrap(
    api.POST("/api/v1/live/{kind}/{source_id}/questions/{question_id}/answered", {
      params: { path: { kind, source_id: id, question_id: questionId } },
    }),
  );
export const raiseHand = (kind: LiveKind, id: string) =>
  unwrap(api.POST("/api/v1/live/{kind}/{source_id}/hand", room(kind, id)));
export const lowerHand = (kind: LiveKind, id: string) =>
  unwrap(api.DELETE("/api/v1/live/{kind}/{source_id}/hand", room(kind, id)));
const floor = (kind: LiveKind, id: string, userId: string) => ({
  params: { path: { kind, source_id: id, user_id: userId } },
});
export const giveFloor = (kind: LiveKind, id: string, userId: string) =>
  unwrap(
    api.POST("/api/v1/live/{kind}/{source_id}/hands/{user_id}/floor", floor(kind, id, userId)),
  );
export const takeFloor = (kind: LiveKind, id: string, userId: string) =>
  unwrap(
    api.DELETE("/api/v1/live/{kind}/{source_id}/hands/{user_id}/floor", floor(kind, id, userId)),
  );

// --- Sales lives of the shop ------------------------------------------------------------------

export const getMySaleLives = () => unwrap(api.GET("/api/v1/me/shop/lives"));
export const planSaleLive = (body: Schemas["SaleLiveInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/shop/lives", { body }));
export const cancelSaleLive = (liveId: string) =>
  unwrap(
    api.POST("/api/v1/me/shop/lives/{live_id}/cancel", { params: { path: { live_id: liveId } } }),
  );
const pin = (liveId: string, productId: string) => ({
  params: { path: { live_id: liveId, product_id: productId } },
});
export const pinProduct = (liveId: string, productId: string) =>
  unwrap(api.POST("/api/v1/me/shop/lives/{live_id}/pins/{product_id}", pin(liveId, productId)));
export const unpinProduct = (liveId: string, productId: string) =>
  unwrap(api.DELETE("/api/v1/me/shop/lives/{live_id}/pins/{product_id}", pin(liveId, productId)));
