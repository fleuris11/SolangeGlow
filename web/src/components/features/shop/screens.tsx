"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;

export const CartScreen = dynamic(() => import("./cart").then((m) => m.CartScreen), { loading });
export const CheckoutFlow = dynamic(() => import("./checkout").then((m) => m.CheckoutFlow), {
  loading,
});
export const CheckoutDone = dynamic(() => import("./group-pay").then((m) => m.CheckoutDone), {
  loading,
});
export const TestGroupCheckout = dynamic(
  () => import("./group-pay").then((m) => m.TestGroupCheckout),
  { loading },
);
export const OrderList = dynamic(() => import("./orders").then((m) => m.OrderList), { loading });
export const OrderDetail = dynamic(() => import("./order-detail").then((m) => m.OrderDetail), {
  loading,
});
export const WishlistScreen = dynamic(() => import("./wishlist").then((m) => m.WishlistScreen), {
  loading,
});
export const MyShopScreen = dynamic(() => import("./my-shop").then((m) => m.MyShopScreen), {
  loading,
});
export const ProductEditor = dynamic(
  () => import("./product-editor").then((m) => m.ProductEditor),
  { loading },
);
