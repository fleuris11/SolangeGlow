"use client";

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError, hasSession } from "@/lib/api/client";
import { startConversation } from "@/lib/api/messaging";
import { useRouter } from "@/lib/i18n/navigation";

type Props = {
  personId: string;
  /** Drawn by the server page (ADR-004). */
  icon: ReactNode;
  /** Prepared in the composer, e.g. "slot:aicha|2026-10-12T14:00:00Z". */
  query?: string;
  variant?: "primary" | "secondary";
  fullWidth?: boolean;
  label?: string;
};

/** « Write »: opens (or creates) the conversation with this person. */
export function WriteButton({
  personId,
  icon,
  query,
  variant = "secondary",
  fullWidth,
  label,
}: Props) {
  const t = useTranslations("messages");
  const toast = useToast();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  const open = async () => {
    if (!hasSession()) {
      router.push("/auth");
      return;
    }
    setBusy(true);
    try {
      const conversation = await startConversation(personId);
      router.push(`/messages/${conversation.id}${query ? `?${query}` : ""}`);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("startError"), "warning");
      setBusy(false);
    }
  };

  return (
    <Button variant={variant} fullWidth={fullWidth} disabled={busy} onClick={() => void open()}>
      {icon}
      {label ?? t("write")}
    </Button>
  );
}
