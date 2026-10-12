/** Messaging: conversations, messages, requests, quick replies and away message. */
import { api, unwrap, type Schemas } from "./client";

export type Conversation = Schemas["Conversation"];
export type ConversationPage = Schemas["ConversationPage"];
export type Message = Schemas["Message"];
export type MessagePage = Schemas["MessagePage"];
export type Person = Schemas["Person"];
export type ShareCard = Schemas["ShareCard"];
export type ShareInput = Schemas["ShareInputRequest"];
export type MessageInput = Schemas["MessageCreateRequest"];
export type ReportReason = Schemas["MessageReportRequest"]["reason"];

export { getMessagingUnread, messagingUnreadKey } from "./messaging-unread";

export const getConversations = (box: "inbox" | "requests" = "inbox", before?: string) =>
  unwrap(
    api.GET("/api/v1/conversations", {
      params: { query: { box, ...(before ? { before } : {}) } },
    }),
  );

export const startConversation = (personId: string) =>
  unwrap(api.POST("/api/v1/conversations", { body: { person_id: personId } }));

export const getConversation = (id: string) =>
  unwrap(
    api.GET("/api/v1/conversations/{conversation_id}", {
      params: { path: { conversation_id: id } },
    }),
  );

export const updateConversation = (id: string, body: { muted?: boolean; archived?: boolean }) =>
  unwrap(
    api.PATCH("/api/v1/conversations/{conversation_id}", {
      params: { path: { conversation_id: id } },
      body,
    }),
  );

export const acceptRequest = (id: string) =>
  unwrap(
    api.POST("/api/v1/conversations/{conversation_id}/accept", {
      params: { path: { conversation_id: id } },
    }),
  );

export const declineRequest = (id: string) =>
  unwrap(
    api.POST("/api/v1/conversations/{conversation_id}/decline", {
      params: { path: { conversation_id: id } },
    }),
  );

export const getMessages = (id: string, before?: string) =>
  unwrap(
    api.GET("/api/v1/conversations/{conversation_id}/messages", {
      params: { path: { conversation_id: id }, query: before ? { before } : {} },
    }),
  );

export const sendMessage = (id: string, body: MessageInput) =>
  unwrap(
    api.POST("/api/v1/conversations/{conversation_id}/messages", {
      params: { path: { conversation_id: id } },
      body,
    }),
  );

export const markRead = (id: string) =>
  unwrap(
    api.POST("/api/v1/conversations/{conversation_id}/read", {
      params: { path: { conversation_id: id } },
    }),
  );

export const deleteMessage = (id: string) =>
  unwrap(api.DELETE("/api/v1/messages/{message_id}", { params: { path: { message_id: id } } }));

export const reportMessage = (id: string, reason: ReportReason) =>
  unwrap(
    api.POST("/api/v1/messages/{message_id}/report", {
      params: { path: { message_id: id } },
      body: { reason },
    }),
  );

export const getQuickReplies = () => unwrap(api.GET("/api/v1/me/pro/quick-replies"));

export const saveQuickReplies = (texts: string[]) =>
  unwrap(api.PUT("/api/v1/me/pro/quick-replies", { body: { texts } }));

export const getAwayMessage = () => unwrap(api.GET("/api/v1/me/pro/away-message"));

export const saveAwayMessage = (body: { enabled: boolean; text: string }) =>
  unwrap(api.PUT("/api/v1/me/pro/away-message", { body }));

/** A picture or a voice note for a message (private: only the conversation sees it). */
export function uploadMessageFile(file: Blob, purpose: "message_photo" | "voice_note") {
  const form = new FormData();
  form.append("file", file, file instanceof File ? file.name : "voice.webm");
  form.append("purpose", purpose);
  return unwrap(
    api.POST("/api/v1/media", { body: form as unknown as Schemas["MediaUploadRequest"] }),
  );
}

export const getMediaStatus = (id: string) =>
  unwrap(api.GET("/api/v1/media/{asset_id}", { params: { path: { asset_id: id } } }));
