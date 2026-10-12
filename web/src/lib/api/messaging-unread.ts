/** The unread counter of the menu, apart from the rest of the messaging (ADR-004). */
import { api, unwrap } from "./client";

export const messagingUnreadKey = ["messaging", "unread"] as const;

export const getMessagingUnread = () => unwrap(api.GET("/api/v1/me/messaging/unread"));
