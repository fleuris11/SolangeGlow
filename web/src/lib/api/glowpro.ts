/** Glow Pro: the plans, the dashboard, the widget, the salon tools and invoices. */
import { api, unwrap, type Schemas } from "./client";

export type MyGlowPro = Schemas["MyGlowPro"];
export type GlowPlan = Schemas["GlowPlan"];
export type GlowFeature = Schemas["GlowFeatureEnum"];
export type Dashboard = Schemas["Dashboard"];
export type PeriodStats = Schemas["PeriodStats"];
export type WidgetSettings = Schemas["Widget"];
export type Package = Schemas["Package"];
export type SoldPackage = Schemas["SoldPackage"];
export type ClientFile = Schemas["ClientFile"];
export type GiftCard = Schemas["GiftCard"];
export type GiftCardOffer = Schemas["GiftCardOffer"];
export type StockItem = Schemas["StockItem"];
export type StockMovement = Schemas["Movement"];
export type OnSitePayment = Schemas["OnSitePayment"];
export type OnSiteMethod = Schemas["OnSiteMethodEnum"];
export type Campaign = Schemas["Campaign"];
export type Document = Schemas["Document"];
export type Billing = Schemas["Billing"];

// --- My plan -------------------------------------------------------------------------------------

export const getMyGlowPro = () => unwrap(api.GET("/api/v1/me/glowpro"));
export const startTrial = () =>
  unwrap(api.POST("/api/v1/me/glowpro/trial", { body: { plan: "premium" } }));
export const subscribe = () =>
  unwrap(api.POST("/api/v1/me/glowpro/subscribe", { body: { plan: "premium" } }));
export const cancelPlan = () => unwrap(api.POST("/api/v1/me/glowpro/cancel"));
export const resumePlan = () => unwrap(api.POST("/api/v1/me/glowpro/resume"));

export const getDashboard = (query: { start?: string; end?: string }) =>
  unwrap(api.GET("/api/v1/me/dashboard", { params: { query } }));

export const getWidget = () => unwrap(api.GET("/api/v1/me/widget"));
export const saveWidget = (body: Schemas["WidgetInputRequest"]) =>
  unwrap(api.PUT("/api/v1/me/widget", { body }));

// --- Packages and the client file -----------------------------------------------------------------

export const getPackages = () => unwrap(api.GET("/api/v1/me/salon/packages"));
export const addPackage = (body: Schemas["PackageInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/salon/packages", { body }));
export const getClientFile = (recordId: string) =>
  unwrap(
    api.GET("/api/v1/me/salon/clients/{record_id}", { params: { path: { record_id: recordId } } }),
  );
export const updateClientFile = (
  recordId: string,
  body: Schemas["PatchedClientFileInputRequest"],
) =>
  unwrap(
    api.PATCH("/api/v1/me/salon/clients/{record_id}", {
      params: { path: { record_id: recordId } },
      body,
    }),
  );
export const sellPackage = (recordId: string, body: Schemas["SellPackageInputRequest"]) =>
  unwrap(
    api.POST("/api/v1/me/salon/clients/{record_id}/packages", {
      params: { path: { record_id: recordId } },
      body,
    }),
  );
export const spendSession = (soldId: string) =>
  unwrap(
    api.POST("/api/v1/me/salon/sold/{sold_id}/use", { params: { path: { sold_id: soldId } } }),
  );
export const recordInstallment = (installmentId: string, method: OnSiteMethod) =>
  unwrap(
    api.POST("/api/v1/me/salon/installments/{installment_id}/record", {
      params: { path: { installment_id: installmentId } },
      body: { method },
    }),
  );

// --- Gift cards ----------------------------------------------------------------------------------

export const getGiftCards = (q?: string) =>
  unwrap(api.GET("/api/v1/me/salon/gift-cards", { params: { query: { q } } }));
export const sellGiftCard = (body: Schemas["SellGiftCardInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/salon/gift-cards", { body }));
export const checkGiftCard = (code: string) =>
  unwrap(api.GET("/api/v1/me/salon/gift-cards/check", { params: { query: { code } } }));
export const redeemGiftCard = (body: Schemas["RedeemInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/salon/gift-cards/redeem", { body }));

// --- Stock ---------------------------------------------------------------------------------------

export const getStock = (low?: boolean) =>
  unwrap(api.GET("/api/v1/me/salon/stock", { params: { query: low ? { low: true } : {} } }));
export const addStockItem = (body: Schemas["StockItemInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/salon/stock", { body }));
export const updateStockItem = (itemId: string, body: Schemas["StockItemInputRequest"]) =>
  unwrap(
    api.PUT("/api/v1/me/salon/stock/{item_id}", { params: { path: { item_id: itemId } }, body }),
  );
export const getMovements = (itemId: string) =>
  unwrap(api.GET("/api/v1/me/salon/stock/{item_id}", { params: { path: { item_id: itemId } } }));
export const moveStock = (itemId: string, body: Schemas["StockMoveInputRequest"]) =>
  unwrap(
    api.POST("/api/v1/me/salon/stock/{item_id}/move", {
      params: { path: { item_id: itemId } },
      body,
    }),
  );
export const countStock = (itemId: string, counted: number) =>
  unwrap(
    api.POST("/api/v1/me/salon/stock/{item_id}/count", {
      params: { path: { item_id: itemId } },
      body: { counted },
    }),
  );
export const findByBarcode = (ean: string) =>
  unwrap(api.GET("/api/v1/me/salon/stock/ean/{ean}", { params: { path: { ean: ean } } }));

export const getConsumption = (serviceId: string) =>
  unwrap(
    api.GET("/api/v1/me/salon/services/{service_id}/consumption", {
      params: { path: { service_id: serviceId } },
    }),
  );
export const setConsumption = (serviceId: string, rows: { item_id: string; quantity: number }[]) =>
  unwrap(
    api.PUT("/api/v1/me/salon/services/{service_id}/consumption", {
      params: { path: { service_id: serviceId } },
      body: { rows },
    }),
  );

// --- Payments at the salon and documents ---------------------------------------------------------

export const getPaymentMethods = () => unwrap(api.GET("/api/v1/me/salon/payments/methods"));
export const getOnSitePayments = (query: { day?: string; appointment?: string }) =>
  unwrap(api.GET("/api/v1/me/salon/payments", { params: { query } }));
export const recordPayment = (body: Schemas["OnSitePaymentInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/salon/payments", { body }));
export const cancelOnSitePayment = (paymentId: string, reason: string) =>
  unwrap(
    api.POST("/api/v1/me/salon/payments/{payment_id}/cancel", {
      params: { path: { payment_id: paymentId } },
      body: { reason },
    }),
  );
export const receiptOf = (paymentId: string) =>
  unwrap(
    api.POST("/api/v1/me/salon/payments/{payment_id}/receipt", {
      params: { path: { payment_id: paymentId } },
    }),
  );
export const invoiceOf = (appointmentId: string) =>
  unwrap(
    api.POST("/api/v1/me/salon/appointments/{appointment_id}/invoice", {
      params: { path: { appointment_id: appointmentId } },
    }),
  );
export const getDocuments = () => unwrap(api.GET("/api/v1/me/documents"));
export const creditDocument = (documentId: string, reason: string) =>
  unwrap(
    api.POST("/api/v1/me/documents/{document_id}/credit", {
      params: { path: { document_id: documentId } },
      body: { reason },
    }),
  );
export const getBilling = () => unwrap(api.GET("/api/v1/me/billing"));
export const updateBilling = (body: Schemas["PatchedBillingRequest"]) =>
  unwrap(api.PATCH("/api/v1/me/billing", { body }));

// --- Campaigns -----------------------------------------------------------------------------------

export const getCampaigns = () => unwrap(api.GET("/api/v1/me/salon/campaigns"));
export const addCampaign = (body: Schemas["CampaignInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/salon/campaigns", { body }));
export const getAudience = (campaignId: string) =>
  unwrap(
    api.GET("/api/v1/me/salon/campaigns/{campaign_id}", {
      params: { path: { campaign_id: campaignId } },
    }),
  );
export const sendCampaign = (campaignId: string) =>
  unwrap(
    api.POST("/api/v1/me/salon/campaigns/{campaign_id}/send", {
      params: { path: { campaign_id: campaignId } },
    }),
  );

// --- For clients ---------------------------------------------------------------------------------

export const getOffers = (slug: string) =>
  unwrap(api.GET("/api/v1/pros/{slug}/offers", { params: { path: { slug: slug } } }));
export const buyGiftCard = (slug: string, body: Schemas["BuyGiftCardInputRequest"]) =>
  unwrap(api.POST("/api/v1/pros/{slug}/gift-cards", { params: { path: { slug } }, body }));
export const buyPackage = (slug: string, packageId: string, installments: number) =>
  unwrap(
    api.POST("/api/v1/pros/{slug}/packages/{package_id}/buy", {
      params: { path: { slug, package_id: packageId } },
      body: { installments },
    }),
  );
export const getMySalonItems = () => unwrap(api.GET("/api/v1/salon/mine"));
export const payInstallment = (installmentId: string) =>
  unwrap(
    api.POST("/api/v1/salon/installments/{installment_id}/pay", {
      params: { path: { installment_id: installmentId } },
    }),
  );
export const getUnsubscribe = (token: string) =>
  unwrap(api.GET("/api/v1/unsubscribe/{token}", { params: { path: { token: token } } }));
export const unsubscribe = (token: string) =>
  unwrap(api.POST("/api/v1/unsubscribe/{token}", { params: { path: { token: token } } }));
