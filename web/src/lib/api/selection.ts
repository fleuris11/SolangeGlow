/** France Selection (module 6): catalogue, orders paid through the secure payment, requests. */
import { api, unwrap, type Schemas } from "./client";

export type SelectionProduct = Schemas["SelectionProductDetail"];
export type SelectionSummary = Schemas["SelectionProductSummary"];
export type SelectionOrder = Schemas["SelectionOrder"];
export type SelectionRequest = Schemas["SelectionRequest"];
export type PickupPoint = Schemas["SelectionPickupPoint"];
export type ShippingMode = Schemas["SelectionShippingModeEnum"];

const order = (id: string) => ({ params: { path: { order_id: id } } });
const request = (id: string) => ({ params: { path: { request_id: id } } });

export const getPickupPoints = () => unwrap(api.GET("/api/v1/selection/pickup-points"));

export const placeSelectionOrder = (body: Schemas["SelectionOrderInputRequest"]) =>
  unwrap(api.POST("/api/v1/selection/orders", { body }));

export const getSelectionOrders = () => unwrap(api.GET("/api/v1/selection/orders"));

export const getSelectionOrder = (id: string) =>
  unwrap(api.GET("/api/v1/selection/orders/{order_id}", order(id)));

export const cancelSelectionOrder = (id: string) =>
  unwrap(api.POST("/api/v1/selection/orders/{order_id}/cancel", order(id)));

export const paySelectionOrder = (id: string) =>
  unwrap(api.POST("/api/v1/selection/orders/{order_id}/pay", order(id)));

export const getRequests = () => unwrap(api.GET("/api/v1/selection/requests"));

export const sendRequest = (body: Schemas["SelectionRequestInputRequest"]) =>
  unwrap(api.POST("/api/v1/selection/requests", { body }));

export const orderQuote = (id: string, body: Schemas["SelectionQuoteOrderRequest"]) =>
  unwrap(api.POST("/api/v1/selection/requests/{request_id}/order", { ...request(id), body }));

export const declineQuote = (id: string) =>
  unwrap(api.POST("/api/v1/selection/requests/{request_id}/decline", request(id)));

/** The client's photo of a wished product (seen by the team only). */
export function uploadRequestPhoto(file: Blob) {
  const form = new FormData();
  form.append("file", file, file instanceof File ? file.name : "photo.jpg");
  form.append("purpose", "selection_request");
  return unwrap(
    api.POST("/api/v1/media", { body: form as unknown as Schemas["MediaUploadRequest"] }),
  );
}
