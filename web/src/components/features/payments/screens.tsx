"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useSyncExternalStore, type ReactNode } from "react";

import { buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { hasSession } from "@/lib/api/client";
import { Link } from "@/lib/i18n/navigation";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;
export const PaymentDetail = dynamic(
  () => import("./payment-detail").then((m) => m.PaymentDetail),
  { loading },
);
export const PaymentList = dynamic(() => import("./payment-list").then((m) => m.PaymentList), {
  loading,
});
export const WalletScreen = dynamic(() => import("./wallet").then((m) => m.WalletScreen), {
  loading,
});
export const TestCheckout = dynamic(() => import("./test-checkout").then((m) => m.TestCheckout), {
  loading,
});
export const DemoOrder = dynamic(() => import("./demo-order").then((m) => m.DemoOrder), {
  loading,
});
export const CourierConfirm = dynamic(
  () => import("./courier-confirm").then((m) => m.CourierConfirm),
  { loading },
);

const subscribeNothing = () => () => {};

/** Payments are personal: signed-in people only, others are invited to sign in. */
export function SignedIn({ children }: { children: ReactNode }) {
  const t = useTranslations("payments");
  const signedIn = useSyncExternalStore(subscribeNothing, hasSession, () => null);
  if (signedIn === null) return loading();
  if (!signedIn) {
    return (
      <div className="flex flex-col items-start gap-4">
        <p className="text-lead font-bold">{t("signIn")}</p>
        <Link href="/auth" className={buttonClasses({ size: "lg" })}>
          {t("signInCta")}
        </Link>
      </div>
    );
  }
  return <>{children}</>;
}
