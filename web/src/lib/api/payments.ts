/** Secure payment: payments of both sides, disputes, the seller's wallet (ADR-007). */
import { api, unwrap, type Schemas } from "./client";

export type Payment = Schemas["Payment"];
export type Wallet = Schemas["Wallet"];
export type WalletOverview = Schemas["WalletOverview"];
export type WalletLine = Schemas["WalletLine"];
export type PayoutMethodInput = Schemas["PayoutMethodRequest"];
export type TaxProfile = Schemas["TaxProfile"];
export type DisputeReason = Schemas["OpenDisputeRequest"]["reason"];

const at = (id: string) => ({ params: { path: { payment_id: id } } });

export const getPayments = (role: "buyer" | "seller") =>
  unwrap(api.GET("/api/v1/payments", { params: { query: { role } } }));

export const getPayment = (id: string) => unwrap(api.GET("/api/v1/payments/{payment_id}", at(id)));

export const startCheckout = (id: string) =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/checkout", at(id)));

export const testOutcome = (id: string, outcome: "succeeded" | "failed" | "abandoned") =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/test-outcome", { ...at(id), body: { outcome } }));

export const ship = (id: string, body: Schemas["ShipRequest"]) =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/ship", { ...at(id), body }));

export const markDelivered = (id: string, proofMediaId: string) =>
  unwrap(
    api.POST("/api/v1/payments/{payment_id}/delivered", {
      ...at(id),
      body: { proof_media_id: proofMediaId },
    }),
  );

export const confirmCode = (id: string, code: string) =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/confirm", { ...at(id), body: { code } }));

export const courierLink = (id: string) =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/courier-link", at(id)));

export const cancelPayment = (id: string) =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/cancel", at(id)));

export const newCode = (id: string) =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/new-code", at(id)));

export const openDispute = (
  id: string,
  body: { reason: DisputeReason; description?: string; media_ids?: string[] },
) => unwrap(api.POST("/api/v1/payments/{payment_id}/dispute", { ...at(id), body }));

export const addEvidence = (id: string, body: { text?: string; media_id?: string | null }) =>
  unwrap(api.POST("/api/v1/payments/{payment_id}/dispute/evidence", { ...at(id), body }));

export const getCourierPayment = (token: string) =>
  unwrap(api.GET("/api/v1/payments/courier/{token}", { params: { path: { token } } }));

export const courierConfirm = (token: string, code: string) =>
  unwrap(
    api.POST("/api/v1/payments/courier/{token}", { params: { path: { token } }, body: { code } }),
  );

export const getWallet = () => unwrap(api.GET("/api/v1/me/wallet"));

export const getWalletHistory = (currency: string) =>
  unwrap(api.GET("/api/v1/me/wallet/history", { params: { query: { currency } } }));

export const requestPayout = (amountMinor: number, currency: string) =>
  unwrap(api.POST("/api/v1/me/payouts", { body: { amount_minor: amountMinor, currency } }));

export const savePayoutMethod = (body: PayoutMethodInput) =>
  unwrap(api.PUT("/api/v1/me/payout-methods", { body }));

export async function getTaxProfile(): Promise<TaxProfile | null> {
  const { data, response } = await api.GET("/api/v1/me/tax-profile");
  return response.ok ? (data as TaxProfile) : null;
}

export const saveTaxProfile = (body: Schemas["TaxProfileRequest"]) =>
  unwrap(api.PUT("/api/v1/me/tax-profile", { body }));

/** Pictures of a dispute or a delivery (private: only the people of the payment see them). */
export function uploadPaymentPicture(file: Blob, purpose: "delivery_proof" | "dispute_evidence") {
  const form = new FormData();
  form.append("file", file, file instanceof File ? file.name : "photo.jpg");
  form.append("purpose", purpose);
  return unwrap(
    api.POST("/api/v1/media", { body: form as unknown as Schemas["MediaUploadRequest"] }),
  );
}

export const getMedia = (id: string) =>
  unwrap(api.GET("/api/v1/media/{asset_id}", { params: { path: { asset_id: id } } }));
