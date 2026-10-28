"use client";

import { Phone, PhoneIncoming, VideoCamera } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { getCallState, startCall } from "@/lib/api/calls";
import { ApiError } from "@/lib/api/client";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { isConnected, subscribe } from "@/lib/messaging/bus";

export const callStateKey = (conversationId: string) => ["call-state", conversationId];

function useCallState(conversationId: string) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: callStateKey(conversationId),
    queryFn: () => getCallState(conversationId),
    // Without the live connection, look for a ringing call every 5 s.
    refetchInterval: () => (isConnected() ? 30_000 : 5_000),
    retry: false,
  });
  useEffect(
    () =>
      subscribe((event) => {
        if (
          (event.type === "call" || event.type === "call_incoming") &&
          event.call.conversation_id === conversationId
        ) {
          void queryClient.invalidateQueries({ queryKey: callStateKey(conversationId) });
        }
      }),
    [conversationId, queryClient],
  );
  return query;
}

/** « Call » and « Video » in the header of a conversation (when she may call). */
export function CallButtons({ conversationId }: { conversationId: string }) {
  const t = useTranslations("calls");
  const toast = useToast();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const { data } = useCallState(conversationId);
  if (!data?.can_call || data.active) return null;

  const call = async (video: boolean) => {
    setBusy(true);
    try {
      const joined = await startCall(conversationId, video);
      router.push(`/appel/${joined.call.id}`);
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
      setBusy(false);
    }
  };

  return (
    <>
      <Button
        variant="quiet"
        className="w-12 shrink-0 px-0 sm:w-auto sm:px-3"
        disabled={busy}
        onClick={() => void call(false)}
      >
        <Phone aria-hidden size={22} weight="bold" />
        <span className="sr-only sm:not-sr-only">{t("audio")}</span>
      </Button>
      <Button
        variant="quiet"
        className="w-12 shrink-0 px-0 sm:w-auto sm:px-3"
        disabled={busy}
        onClick={() => void call(true)}
      >
        <VideoCamera aria-hidden size={22} weight="bold" />
        <span className="sr-only sm:not-sr-only">{t("video")}</span>
      </Button>
    </>
  );
}

/** A call going on in this conversation: come in (or answer). */
export function ActiveCallBanner({ conversationId }: { conversationId: string }) {
  const t = useTranslations("calls");
  const { data } = useCallState(conversationId);
  const call = data?.active;
  if (!call) return null;
  const ringingForMe = call.status === "ringing" && call.my_state === "invited";
  const name = call.mine
    ? (call.people[0]?.name ?? "")
    : (call.people.find((p) => p.id === call.caller_id)?.name ?? call.people[0]?.name ?? "");
  return (
    <div role="status" className="bg-poudre mx-4 mt-3 flex items-center gap-3 rounded-2xl p-3">
      <PhoneIncoming aria-hidden size={28} weight="fill" className="text-hibiscus shrink-0" />
      <p className="min-w-0 flex-1 font-bold">
        {ringingForMe ? t("ringingFrom", { name }) : t("ongoing")}
      </p>
      <Link
        href={`/appel/${call.id}${ringingForMe ? "?answer=1" : ""}`}
        className={buttonClasses({ className: "shrink-0" })}
      >
        {ringingForMe ? t("answer") : t("rejoin")}
      </Link>
    </div>
  );
}
