"use client";

import {
  CalendarPlus,
  CircleNotch,
  ImageSquare,
  PaperPlaneRight,
  Scissors,
  X,
} from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Sheet } from "@/components/ui/sheet";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  getMediaStatus,
  getQuickReplies,
  uploadMessageFile,
  type MessageInput,
  type ShareInput,
} from "@/lib/api/messaging";
import { getMyPro, myProQueryKey } from "@/lib/api/pros";
import { send as sendEvent } from "@/lib/messaging/bus";

import { HoldToRecord } from "./hold-to-record";

export type Attachment = { share: ShareInput; label: string };

type Props = {
  conversationId: string;
  isPro: boolean;
  attachment: Attachment | null;
  onAttachmentChange: (value: Attachment | null) => void;
  onSend: (body: MessageInput) => void;
};

async function waitReady(id: string) {
  for (let attempt = 0; attempt < 60; attempt++) {
    const media = await getMediaStatus(id);
    if (media.status !== "pending" && media.status !== "processing") return media;
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  return getMediaStatus(id);
}

/** Write, attach a picture, hold to talk; pros also send a service or a free slot. */
export function Composer({ conversationId, isPro, attachment, onAttachmentChange, onSend }: Props) {
  const t = useTranslations("messages.composer");
  const locale = useLocale();
  const toast = useToast();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<"photo" | "voice" | null>(null);
  const [sheet, setSheet] = useState<"service" | "slot" | null>(null);
  const [slotAt, setSlotAt] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const lastTyping = useRef(0);
  const quick = useQuery({ queryKey: ["quick-replies"], queryFn: getQuickReplies, enabled: isPro });
  const pro = useQuery({ queryKey: myProQueryKey, queryFn: getMyPro, enabled: isPro });
  const proSlug = pro.data?.status === "published" ? pro.data.slug : null;

  const typing = () => {
    const now = Date.now();
    if (now - lastTyping.current > 3000) {
      lastTyping.current = now;
      sendEvent({ type: "typing", conversation: conversationId });
    }
  };

  const submit = () => {
    const words = text.trim();
    if (!words && !attachment) return;
    onSend({ text: words, ...(attachment ? { share: attachment.share } : {}) });
    setText("");
    onAttachmentChange(null);
  };

  const sendFile = async (file: Blob, purpose: "message_photo" | "voice_note") => {
    setBusy(purpose === "voice_note" ? "voice" : "photo");
    try {
      const uploaded = await uploadMessageFile(file, purpose);
      const ready = await waitReady(uploaded.id);
      if (ready.status !== "ready") {
        toast(ready.error || t("fileRefused"), "warning");
        return;
      }
      onSend({ media_id: ready.id, text: purpose === "message_photo" ? text.trim() : "" });
      if (purpose === "message_photo") setText("");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("offlineFile"), "warning");
    } finally {
      setBusy(null);
    }
  };

  const services = pro.data?.services.filter((service) => service.is_active) ?? [];
  const canSend = !!text.trim() || !!attachment;

  return (
    <div className="flex flex-col gap-2">
      {isPro && (quick.data?.texts.length ?? 0) > 0 && (
        <div
          className="-mx-4 flex [scrollbar-width:none] gap-2 overflow-x-auto px-4"
          role="group"
          aria-label={t("quickReplies")}
        >
          {quick.data?.texts.map((reply) => (
            <Chip key={reply} onClick={() => setText(reply)}>
              {reply}
            </Chip>
          ))}
        </div>
      )}
      {attachment && (
        <div className="bg-poudre rounded-card flex items-center gap-3 p-3">
          <p className="flex-1 font-bold">{attachment.label}</p>
          <Button variant="quiet" onClick={() => onAttachmentChange(null)}>
            <X aria-hidden size={20} weight="bold" />
            {t("removeCard")}
          </Button>
        </div>
      )}
      {busy && (
        <p className="text-small text-prune-doux flex items-center gap-2" role="status">
          <CircleNotch aria-hidden size={18} className="animate-spin" />
          {busy === "photo" ? t("preparingPhoto") : t("preparingVoice")}
        </p>
      )}
      <div className="flex items-end gap-2">
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          className="sr-only"
          tabIndex={-1}
          aria-label={t("photo")}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void sendFile(file, "message_photo");
            event.target.value = "";
          }}
        />
        <button
          type="button"
          aria-label={t("photo")}
          disabled={!!busy}
          onClick={() => fileInput.current?.click()}
          className="bg-poudre text-prune inline-flex size-12 shrink-0 items-center justify-center rounded-full disabled:opacity-50"
        >
          <ImageSquare aria-hidden size={26} weight="bold" />
        </button>
        <label htmlFor="message-text" className="sr-only">
          {t("label")}
        </label>
        <textarea
          id="message-text"
          rows={1}
          maxLength={2000}
          value={text}
          placeholder={t("placeholder")}
          onChange={(event) => {
            setText(event.target.value);
            typing();
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              submit();
            }
          }}
          className="rounded-field bg-poudre focus:border-hibiscus [field-sizing:content] max-h-40 min-h-12 flex-1 resize-none border-2 border-transparent px-4 py-3 outline-none"
        />
        {canSend ? (
          <button
            type="button"
            onClick={submit}
            className="bg-hibiscus text-sur-hibiscus inline-flex min-h-12 shrink-0 items-center gap-1 rounded-full px-4 font-bold"
          >
            <PaperPlaneRight aria-hidden size={22} weight="fill" />
            {t("send")}
          </button>
        ) : (
          <HoldToRecord onRecorded={(blob) => void sendFile(blob, "voice_note")} />
        )}
      </div>
      {isPro && proSlug && (
        <div className="flex flex-wrap gap-2">
          <Button variant="quiet" onClick={() => setSheet("service")}>
            <Scissors aria-hidden size={20} weight="bold" />
            {t("shareService")}
          </Button>
          <Button variant="quiet" onClick={() => setSheet("slot")}>
            <CalendarPlus aria-hidden size={20} weight="bold" />
            {t("shareSlot")}
          </Button>
        </div>
      )}

      <Sheet
        open={sheet === "service"}
        onOpenChange={(open) => !open && setSheet(null)}
        title={t("chooseService")}
      >
        {pro.isPending ? (
          <p role="status">{t("loading")}</p>
        ) : services.length === 0 ? (
          <p className="text-prune-doux">{t("noService")}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {services.map((service) => (
              <li key={service.id}>
                <Button
                  variant="secondary"
                  fullWidth
                  onClick={() => {
                    onAttachmentChange({
                      share: { kind: "service", id: service.id },
                      label: t("serviceCard", { name: service.name }),
                    });
                    setSheet(null);
                  }}
                >
                  {service.name}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Sheet>
      <Sheet
        open={sheet === "slot"}
        onOpenChange={(open) => !open && setSheet(null)}
        title={t("chooseSlot")}
      >
        <div className="flex flex-col gap-3">
          <label htmlFor="slot-at" className="font-bold">
            {t("slotWhen")}
          </label>
          <input
            id="slot-at"
            type="datetime-local"
            value={slotAt}
            onChange={(event) => setSlotAt(event.target.value)}
            className="rounded-field bg-poudre focus:border-hibiscus min-h-14 border-2 border-transparent px-4 outline-none"
          />
          <Button
            size="lg"
            disabled={!slotAt || !proSlug}
            onClick={() => {
              const when = new Date(slotAt);
              onAttachmentChange({
                share: { kind: "slot", pro: proSlug ?? "", starts_at: when.toISOString() },
                label: t("slotCard", {
                  when: new Intl.DateTimeFormat(locale, {
                    dateStyle: "full",
                    timeStyle: "short",
                  }).format(when),
                }),
              });
              setSheet(null);
            }}
          >
            {t("attachSlot")}
          </Button>
        </div>
      </Sheet>
    </div>
  );
}
