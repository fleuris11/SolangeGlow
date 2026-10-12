"use client";

import {
  ChatCircleText,
  EyeSlash,
  FacebookLogo,
  Flag,
  LinkSimple,
  Prohibit,
  TiktokLogo,
  Trash,
  WhatsappLogo,
} from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Sheet } from "@/components/ui/sheet";
import { useToast } from "@/components/ui/toast";
import { ApiError, hasSession } from "@/lib/api/client";
import { getConversations } from "@/lib/api/messaging";
import {
  block,
  deletePost,
  hide,
  report,
  share,
  type ReportReason,
  type ShareNetwork,
} from "@/lib/api/social";
import { useRouter } from "@/lib/i18n/navigation";

const REASONS: ReportReason[] = [
  "spam",
  "nudity",
  "harassment",
  "hate",
  "scam",
  "minor",
  "violence",
  "other",
];

/** WhatsApp, Facebook, TikTok (through the copied link) or copy the link (with its preview). */
export function ShareSheet({
  postId,
  url,
  onClose,
}: {
  postId: string;
  url: string;
  onClose: () => void;
}) {
  const t = useTranslations("social.share");
  const toast = useToast();
  const router = useRouter();
  const [picking, setPicking] = useState(false);
  const conversations = useQuery({
    queryKey: ["conversations", "inbox"],
    queryFn: () => getConversations("inbox"),
    enabled: picking,
  });

  const go = async (network: ShareNetwork) => {
    const links = await share(postId, network).catch(() => null);
    if (network === "whatsapp" && links) window.open(links.whatsapp, "_blank", "noopener");
    else if (network === "facebook" && links) window.open(links.facebook, "_blank", "noopener");
    else if (network === "tiktok" && navigator.share) {
      try {
        await navigator.share({ url });
      } catch {
        // Closed by the person.
      }
    } else {
      await navigator.clipboard?.writeText(url);
      toast(network === "tiktok" ? t("tiktokCopied") : t("copied"), "success");
    }
    onClose();
  };

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()} title={t("title")}>
      <div className="flex flex-col gap-3">
        <Button size="lg" fullWidth onClick={() => void go("whatsapp")}>
          <WhatsappLogo aria-hidden size={26} weight="bold" />
          WhatsApp
        </Button>
        <Button variant="secondary" fullWidth onClick={() => void go("facebook")}>
          <FacebookLogo aria-hidden size={24} weight="bold" />
          Facebook
        </Button>
        <Button variant="secondary" fullWidth onClick={() => void go("tiktok")}>
          <TiktokLogo aria-hidden size={24} weight="bold" />
          TikTok
        </Button>
        <Button variant="quiet" fullWidth onClick={() => void go("link")}>
          <LinkSimple aria-hidden size={24} weight="bold" />
          {t("copy")}
        </Button>
        <Button
          variant="quiet"
          fullWidth
          aria-expanded={picking}
          onClick={() => (hasSession() ? setPicking(true) : router.push("/auth"))}
        >
          <ChatCircleText aria-hidden size={24} weight="bold" />
          {t("toMessage")}
        </Button>
        {picking && (
          <div className="flex flex-col gap-2">
            <p className="font-bold">{t("toWhom")}</p>
            {conversations.isPending ? (
              <p role="status">{t("loading")}</p>
            ) : (conversations.data?.results.length ?? 0) === 0 ? (
              <p className="text-prune-doux">{t("noConversation")}</p>
            ) : (
              conversations.data?.results.slice(0, 8).map((conversation) => (
                <Button
                  key={conversation.id}
                  variant="secondary"
                  fullWidth
                  onClick={() => {
                    onClose();
                    router.push(`/messages/${conversation.id}?share=post:${postId}`);
                  }}
                >
                  {conversation.title}
                </Button>
              ))
            )}
          </div>
        )}
      </div>
    </Sheet>
  );
}

/** Report, hide, block, or delete (her own post). */
export function MoreSheet({
  postId,
  authorId,
  authorName,
  isMine,
  onClose,
  onGone,
}: {
  postId: string;
  authorId: string;
  authorName: string;
  isMine: boolean;
  onClose: () => void;
  onGone: () => void;
}) {
  const t = useTranslations("social.more");
  const toast = useToast();
  const router = useRouter();
  const [reasons, setReasons] = useState(false);
  const [confirmBlock, setConfirmBlock] = useState(false);

  const run = async (action: () => Promise<unknown>, message: string, gone = true) => {
    if (!hasSession()) {
      router.push("/auth");
      return;
    }
    try {
      await action();
      toast(message, "success");
      if (gone) onGone();
      onClose();
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    }
  };

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()} title={t("title")}>
      {reasons ? (
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 font-bold">{t("why")}</legend>
          <div className="flex flex-wrap gap-2">
            {REASONS.map((reason) => (
              <Chip
                key={reason}
                onClick={() => void run(() => report("post", postId, reason), t("reported"), false)}
              >
                {t(`reasons.${reason}`)}
              </Chip>
            ))}
          </div>
        </fieldset>
      ) : confirmBlock ? (
        <div className="flex flex-col gap-3">
          <p>{t("blockText", { name: authorName })}</p>
          <Button
            size="lg"
            fullWidth
            onClick={() =>
              void run(() => block(authorId, true), t("blocked", { name: authorName }))
            }
          >
            <Prohibit aria-hidden size={24} weight="bold" />
            {t("blockConfirm", { name: authorName })}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {isMine ? (
            <Button
              variant="secondary"
              fullWidth
              onClick={() => void run(() => deletePost(postId), t("deleted"))}
            >
              <Trash aria-hidden size={24} />
              {t("delete")}
            </Button>
          ) : (
            <>
              <Button variant="secondary" fullWidth onClick={() => setReasons(true)}>
                <Flag aria-hidden size={24} />
                {t("report")}
              </Button>
              <Button
                variant="secondary"
                fullWidth
                onClick={() => void run(() => hide("post", postId), t("hiddenPost"))}
              >
                <EyeSlash aria-hidden size={24} />
                {t("hidePost")}
              </Button>
              <Button
                variant="secondary"
                fullWidth
                onClick={() =>
                  void run(() => hide("person", authorId), t("hiddenPerson", { name: authorName }))
                }
              >
                <EyeSlash aria-hidden size={24} />
                {t("hidePerson", { name: authorName })}
              </Button>
              <Button variant="quiet" fullWidth onClick={() => setConfirmBlock(true)}>
                <Prohibit aria-hidden size={24} />
                {t("block", { name: authorName })}
              </Button>
            </>
          )}
        </div>
      )}
    </Sheet>
  );
}
