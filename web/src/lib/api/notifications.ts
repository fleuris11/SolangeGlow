import { api, unwrap, type Schemas } from "./client";

export type Notification = Schemas["Notification"];

export const notificationsQueryKey = ["notifications"] as const;
export const unreadQueryKey = ["notifications", "unread"] as const;

export const listNotifications = (cursor?: string) =>
  unwrap(api.GET("/api/v1/notifications", { params: { query: cursor ? { cursor } : {} } }));

export const getUnreadCount = () => unwrap(api.GET("/api/v1/notifications/unread-count"));

/** Without ids: everything is marked as read. */
export const markRead = (ids?: string[]) =>
  unwrap(api.POST("/api/v1/notifications/read", { body: ids ? { ids } : {} }));

export const sendTestNotification = () => unwrap(api.POST("/api/v1/notifications/test"));

export const getPushKey = () => unwrap(api.GET("/api/v1/notifications/push/key"));

export const savePushSubscription = (body: Schemas["PushSubscribeRequest"]) =>
  unwrap(api.POST("/api/v1/notifications/push/subscriptions", { body }));

export const deletePushSubscription = (endpoint: string) =>
  unwrap(api.POST("/api/v1/notifications/push/unsubscribe", { body: { endpoint } }));
