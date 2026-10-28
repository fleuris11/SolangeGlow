/** Shops (module 4): products, cart, checkout, orders, wishlist and « My shop ». */
import { api, unwrap, type Schemas } from "./client";

export type ProductSummary = Schemas["ProductSummary"];
export type ProductDetail = Schemas["ProductDetail"];
export type ShopPage = Schemas["ShopPage"];
export type Cart = Schemas["Cart"];
export type CartShop = Schemas["CartShop"];
export type Quote = Schemas["Quote"];
export type Order = Schemas["Order"];
export type MyShop = Schemas["MyShop"];
export type MyProduct = Schemas["MyProduct"];
export type Promotions = Schemas["Promotions"];
export type Stats = Schemas["Stats"];
export type PaymentGroup = Schemas["PaymentGroup"];
export type DeliveryMode = Schemas["ShopChoiceRequest"]["delivery_mode"];
export type ShopChoice = Schemas["ShopChoiceRequest"];
export type ProductInput = Schemas["ProductInputRequest"];
export type VariantInput = Schemas["VariantInputRequest"];

const order = (id: string) => ({ params: { path: { order_id: id } } });
const product = (id: string) => ({ params: { path: { product_id: id } } });

// --- Public --------------------------------------------------------------------------------------

export const getProduct = (id: string) =>
  unwrap(api.GET("/api/v1/shop/products/{product_id}", product(id)));

export const getProductReviews = (id: string) =>
  unwrap(api.GET("/api/v1/shop/products/{product_id}/reviews", product(id)));

export const getCategories = () => unwrap(api.GET("/api/v1/shop/categories"));

// --- Cart and checkout ---------------------------------------------------------------------------

export const getCart = () => unwrap(api.GET("/api/v1/shop/cart"));

export const addToCart = (body: {
  variant_id?: string;
  bundle_id?: string;
  quantity: number;
  sale_live_id?: string;
}) => unwrap(api.POST("/api/v1/shop/cart/items", { body }));

export const setCartQuantity = (itemId: string, quantity: number) =>
  unwrap(
    api.PATCH("/api/v1/shop/cart/items/{item_id}", {
      params: { path: { item_id: itemId } },
      body: { quantity },
    }),
  );

export const removeFromCart = (itemId: string) =>
  unwrap(
    api.DELETE("/api/v1/shop/cart/items/{item_id}", { params: { path: { item_id: itemId } } }),
  );

export const getQuote = (shops: ShopChoice[]) =>
  unwrap(api.POST("/api/v1/shop/checkout/quote", { body: { shops } }));

export const placeOrders = (body: Schemas["CheckoutInputRequest"]) =>
  unwrap(api.POST("/api/v1/shop/checkout", { body }));

export const getPaymentGroup = (id: string) =>
  unwrap(api.GET("/api/v1/payments/groups/{group_id}", { params: { path: { group_id: id } } }));

export const testGroupOutcome = (id: string, outcome: "succeeded" | "failed" | "abandoned") =>
  unwrap(
    api.POST("/api/v1/payments/groups/{group_id}/test-outcome", {
      params: { path: { group_id: id } },
      body: { outcome },
    }),
  );

// --- Orders --------------------------------------------------------------------------------------

export const getOrders = (role: "buyer" | "seller", status?: string) =>
  unwrap(api.GET("/api/v1/shop/orders", { params: { query: { role, status } } }));

export const getOrder = (id: string) =>
  unwrap(api.GET("/api/v1/shop/orders/{order_id}", order(id)));

export const prepareOrder = (id: string) =>
  unwrap(api.POST("/api/v1/shop/orders/{order_id}/prepare", order(id)));

export const shipOrder = (id: string, body: Schemas["ShipInputRequest"]) =>
  unwrap(api.POST("/api/v1/shop/orders/{order_id}/ship", { ...order(id), body }));

export const orderReady = (id: string) =>
  unwrap(api.POST("/api/v1/shop/orders/{order_id}/ready", order(id)));

export const cancelOrder = (id: string) =>
  unwrap(api.POST("/api/v1/shop/orders/{order_id}/cancel", order(id)));

export const payOrder = (id: string) =>
  unwrap(api.POST("/api/v1/shop/orders/{order_id}/pay", order(id)));

// --- Wishlist and alerts -------------------------------------------------------------------------

export const getWishlist = () => unwrap(api.GET("/api/v1/shop/wishlist"));

export const wish = (productId: string, on: boolean) =>
  on
    ? unwrap(api.PUT("/api/v1/shop/wishlist/{product_id}", product(productId)))
    : unwrap(api.DELETE("/api/v1/shop/wishlist/{product_id}", product(productId)));

export const watchStock = (variantId: string, on: boolean) => {
  const at = { params: { path: { variant_id: variantId } } };
  return on
    ? unwrap(api.PUT("/api/v1/shop/alerts/{variant_id}", at))
    : unwrap(api.DELETE("/api/v1/shop/alerts/{variant_id}", at));
};

// --- « My shop » ---------------------------------------------------------------------------------

export const getMyShop = () => unwrap(api.GET("/api/v1/me/shop"));

export const updateMyShop = (body: Schemas["PatchedShopSettingsInputRequest"]) =>
  unwrap(api.PATCH("/api/v1/me/shop", { body }));

export const addZone = (body: Schemas["ZoneInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/shop/zones", { body }));

export const deleteZone = (id: string) =>
  unwrap(api.DELETE("/api/v1/me/shop/zones/{zone_id}", { params: { path: { zone_id: id } } }));

export const getMyProducts = () => unwrap(api.GET("/api/v1/me/shop/products"));

export const getMyProduct = (id: string) =>
  unwrap(api.GET("/api/v1/me/shop/products/{product_id}", product(id)));

export const createProduct = (body: ProductInput) =>
  unwrap(api.POST("/api/v1/me/shop/products", { body }));

export const updateProduct = (id: string, body: ProductInput) =>
  unwrap(api.PUT("/api/v1/me/shop/products/{product_id}", { ...product(id), body }));

export const deleteProduct = (id: string) =>
  unwrap(api.DELETE("/api/v1/me/shop/products/{product_id}", product(id)));

export const publishProduct = (id: string) =>
  unwrap(api.POST("/api/v1/me/shop/products/{product_id}/publish", product(id)));

export const pauseProduct = (id: string) =>
  unwrap(api.POST("/api/v1/me/shop/products/{product_id}/pause", product(id)));

export const setStock = (variantId: string, stock: number) =>
  unwrap(
    api.PATCH("/api/v1/me/shop/variants/{variant_id}", {
      params: { path: { variant_id: variantId } },
      body: { stock },
    }),
  );

export const getPromotions = () => unwrap(api.GET("/api/v1/me/shop/promotions"));

export const createPromo = (body: Schemas["PromoInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/shop/promos", { body }));

export const deletePromo = (id: string) =>
  unwrap(api.DELETE("/api/v1/me/shop/promos/{promo_id}", { params: { path: { promo_id: id } } }));

export const createFlashSale = (body: Schemas["FlashSaleInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/shop/flash-sales", { body }));

export const endFlashSale = (id: string) =>
  unwrap(
    api.DELETE("/api/v1/me/shop/flash-sales/{sale_id}", { params: { path: { sale_id: id } } }),
  );

export const createBundle = (body: Schemas["BundleInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/shop/bundles", { body }));

export const deleteBundle = (id: string) =>
  unwrap(
    api.DELETE("/api/v1/me/shop/bundles/{bundle_id}", { params: { path: { bundle_id: id } } }),
  );

export const getShopStats = () => unwrap(api.GET("/api/v1/me/shop/stats"));

/** Pictures, video and voice of a product (public once the product is online). */
export function uploadShopMedia(
  file: Blob,
  purpose: "product_photo" | "product_video" | "product_voice",
  name?: string,
) {
  const form = new FormData();
  form.append("file", file, name ?? (file instanceof File ? file.name : "media"));
  form.append("purpose", purpose);
  return unwrap(
    api.POST("/api/v1/media", { body: form as unknown as Schemas["MediaUploadRequest"] }),
  );
}
