"use client";

import { Phone, PhoneDisconnect } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { declineCall, getCall, type Call } from "@/lib/api/calls";
import { useMe } from "@/lib/auth/use-me";
import { usePathname, useRouter } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { subscribe } from "@/lib/messaging/bus";

/** « Awa is calling you »: shown on any screen when a call rings for her (live event). */
export function IncomingCall() {
  const t = useTranslations("calls");
  const router = useRouter();
  const pathname = usePathname();
  const { data: me } = useMe();
  const [call, setCall] = useState<Call | null>(null);

  useEffect(
    () =>
      subscribe((event) => {
        if (event.type === "call_incoming" && event.call.caller_id !== me?.id) {
          if (pathname.startsWith("/appel/")) return;
          void getCall(event.call.id)
            .then((found) => {
              if (found.status === "ringing" && found.my_state === "invited") {
                setCall(found);
                navigator.vibrate?.([400, 200, 400, 200, 400]);
              }
            })
            .catch(() => undefined);
        } else if (event.type === "call" && event.call.status !== "ringing") {
          setCall((current) => (current?.id === event.call.id ? null : current));
        }
      }),
    [me?.id, pathname],
  );

  if (!call) return null;
  const caller = call.people.find((p) => p.id === call.caller_id) ?? call.people[0];
  const name = call.is_dispute ? t("disputeCall") : (caller?.name ?? t("someone"));

  return (
    <Sheet
      open
      onOpenChange={(open) => !open && setCall(null)}
      title={t("callingYou", { name })}
      description={call.kind === "video" ? t("incomingVideo") : t("incomingAudio")}
    >
      <div className="flex flex-col items-center gap-6">
        <Avatar name={name} src={mediaSrc(caller?.photo, "medium")} size="lg" halo />
        <div className="grid w-full grid-cols-2 gap-3">
          <Button
            variant="secondary"
            size="lg"
            onClick={() => {
              void declineCall(call.id).catch(() => undefined);
              setCall(null);
            }}
          >
            <PhoneDisconnect aria-hidden size={24} weight="bold" />
            {t("decline")}
          </Button>
          <Button
            size="lg"
            onClick={() => {
              setCall(null);
              router.push(`/appel/${call.id}?answer=1`);
            }}
          >
            <Phone aria-hidden size={24} weight="fill" />
            {t("answer")}
          </Button>
        </div>
      </div>
    </Sheet>
  );
}
