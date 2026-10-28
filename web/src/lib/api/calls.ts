/** Audio and video calls of the messaging (no phone number shown), and the call log. */
import { api, unwrap, type Schemas } from "./client";

export type Call = Schemas["Call"];
export type CallJoin = Schemas["CallJoin"];
export type CallState = Schemas["CallState"];
export type CallPage = Schemas["CallPage"];

const conversation = (id: string) => ({ params: { path: { conversation_id: id } } });
const call = (id: string) => ({ params: { path: { call_id: id } } });

export const getCallState = (conversationId: string) =>
  unwrap(api.GET("/api/v1/conversations/{conversation_id}/call", conversation(conversationId)));
export const startCall = (conversationId: string, video: boolean) =>
  unwrap(
    api.POST("/api/v1/conversations/{conversation_id}/call", {
      ...conversation(conversationId),
      body: { video },
    }),
  );
export const getCall = (callId: string) => unwrap(api.GET("/api/v1/calls/{call_id}", call(callId)));
export const answerCall = (callId: string) =>
  unwrap(api.POST("/api/v1/calls/{call_id}/answer", call(callId)));
export const declineCall = (callId: string) =>
  unwrap(api.POST("/api/v1/calls/{call_id}/decline", call(callId)));
export const hangUp = (callId: string) =>
  unwrap(api.POST("/api/v1/calls/{call_id}/hang-up", call(callId)));
export const getCallLog = (before?: string) =>
  unwrap(api.GET("/api/v1/me/calls", { params: { query: before ? { before } : {} } }));
