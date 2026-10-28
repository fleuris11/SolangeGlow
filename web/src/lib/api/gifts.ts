/** Diaspora gifts: offering (paid in euros), the secret page of the gift, the follow-up,
 * paying with a Glow gift card. */
import { api, unwrap, type Schemas } from "./client";

export type GiftKind = Schemas["GiftKindEnum"];
export type Occasion = Schemas["GiftCreateRequest"]["occasion"];
export type GiftQuote = Schemas["GiftQuote"];
export type GiftIdeas = Schemas["GiftIdeas"];
export type GiftIdea = Schemas["GiftIdea"];
export type GiftOptions = Schemas["GiftOptions"];
export type GiftSent = Schemas["GiftSent"];
export type GiftReceived = Schemas["GiftReceived"];
export type GiftReception = Schemas["GiftReception"];
export type GiftUse = Schemas["GiftUse"];
export type GiftCreate = Schemas["GiftCreateRequest"];

export const OCCASIONS: Occasion[] = ["mothers_day", "birthday", "wedding", "year_end", "none"];

export type QuoteQuery = {
  kind: GiftKind;
  service?: string;
  variant?: string;
  delivery_mode?: string;
  zone?: string;
  selection_product?: string;
  option?: string;
  amount_minor?: number;
};

export const getGiftIdeas = () => unwrap(api.GET("/api/v1/gifts/ideas"));
export const getGiftQuote = (query: QuoteQuery) =>
  unwrap(api.GET("/api/v1/gifts/quote", { params: { query } }));
export const getProductOptions = (variantId: string) =>
  unwrap(
    api.GET("/api/v1/gifts/products/{variant_id}/options", {
      params: { path: { variant_id: variantId } },
    }),
  );

export const offerGift = (body: GiftCreate) => unwrap(api.POST("/api/v1/gifts", { body }));
export const getSentGifts = () => unwrap(api.GET("/api/v1/gifts"));
export const getReceivedGifts = () => unwrap(api.GET("/api/v1/gifts/received"));

const mine = (id: string) => ({ params: { path: { gift_id: id } } });
export const getSentGift = (id: string) => unwrap(api.GET("/api/v1/gifts/{gift_id}", mine(id)));
export const payGiftAgain = (id: string) =>
  unwrap(api.POST("/api/v1/gifts/{gift_id}/pay", mine(id)));
export const cancelGift = (id: string) =>
  unwrap(api.POST("/api/v1/gifts/{gift_id}/cancel", mine(id)));
export const resendGift = (id: string) =>
  unwrap(api.POST("/api/v1/gifts/{gift_id}/resend", mine(id)));

// --- The page of the gift (secret link) --------------------------------------------------------

const open = (token: string) => ({ params: { path: { token } } });
export const openGift = (token: string) =>
  unwrap(api.GET("/api/v1/gifts/open/{token}", open(token)));
export const claimGift = (token: string) =>
  unwrap(api.POST("/api/v1/gifts/open/{token}/claim", open(token)));
export const bookGift = (token: string, body: Schemas["GiftBookRequest"]) =>
  unwrap(api.POST("/api/v1/gifts/open/{token}/book", { ...open(token), body }));
export const receiveGift = (token: string, body: Schemas["GiftReceiveRequest"]) =>
  unwrap(api.POST("/api/v1/gifts/open/{token}/receive", { ...open(token), body }));
export const giftAsCard = (token: string) =>
  unwrap(api.POST("/api/v1/gifts/open/{token}/as-card", open(token)));
export const answerProof = (token: string, body: Schemas["GiftProofRequest"]) =>
  unwrap(api.POST("/api/v1/gifts/open/{token}/proof", { ...open(token), body }));

export function addGiftPhoto(token: string, file: Blob) {
  const form = new FormData();
  form.append("file", file);
  return unwrap(
    api.POST("/api/v1/gifts/open/{token}/photos", {
      ...open(token),
      body: form as unknown as Schemas["GiftPhotoUploadRequest"],
    }),
  );
}

/** A voice note or a video for the gift; processed in the background. */
export function uploadGiftMessage(file: Blob) {
  const form = new FormData();
  form.append("file", file);
  form.append("purpose", "gift_message");
  return unwrap(
    api.POST("/api/v1/media", { body: form as unknown as Schemas["MediaUploadRequest"] }),
  );
}

// --- The Glow gift card ------------------------------------------------------------------------

export const checkGlowCard = (code: string) =>
  unwrap(api.POST("/api/v1/gifts/cards/check", { body: { code } }));
export const payWithGlowCard = (body: Schemas["GiftPayRequest"]) =>
  unwrap(api.POST("/api/v1/gifts/cards/pay", { body }));
