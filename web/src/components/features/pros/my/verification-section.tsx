"use client";

import { Camera, IdentificationCard, LockKey, SealCheck, ShieldCheck } from "@phosphor-icons/react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { myProQueryKey, sendVerification, type MyPro } from "@/lib/api/pros";

import { SectionFrame } from "./section-frame";

const DOCUMENTS = ["id_card", "passport", "residence_permit", "driving_licence"] as const;

/** Identity document + selfie: the « Verified pro » badge, needed to cash in. */
export function VerificationSection({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.verification");
  const toast = useToast();
  const queryClient = useQueryClient();
  const documentInput = useRef<HTMLInputElement>(null);
  const selfieInput = useRef<HTMLInputElement>(null);
  const [type, setType] = useState<(typeof DOCUMENTS)[number]>("id_card");
  const [document, setDocument] = useState<File | null>(null);
  const [selfie, setSelfie] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const state = pro.verification;
  const canSend = state.status === "none" || state.status === "rejected";

  const send = async () => {
    if (!document || !selfie) return;
    setBusy(true);
    setError(undefined);
    try {
      await sendVerification({ documentType: type, document, selfie });
      await queryClient.invalidateQueries({ queryKey: myProQueryKey });
      toast(t("sent"), "success");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <div
        className={`rounded-card flex gap-3 p-4 ${state.status === "verified" ? "bg-feuille text-lait" : "bg-poudre"}`}
        role="status"
      >
        {state.status === "verified" ? (
          <SealCheck aria-hidden size={28} weight="fill" className="shrink-0" />
        ) : (
          <ShieldCheck aria-hidden size={28} weight="duotone" className="text-hibiscus shrink-0" />
        )}
        <div className="flex flex-col gap-1">
          <p className="font-bold">{t(`state.${state.status}`)}</p>
          {state.status === "rejected" && state.rejection_reason && (
            <p>{t("reason", { reason: state.rejection_reason })}</p>
          )}
          <p className="text-small">
            {state.can_collect_payments ? t("canCollect") : t("cannotCollect")}
          </p>
        </div>
      </div>

      {canSend && (
        <>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("documentType")}</legend>
            <div className="flex flex-wrap gap-2">
              {DOCUMENTS.map((value) => (
                <Chip key={value} selected={type === value} onClick={() => setType(value)}>
                  {t(`documents.${value}`)}
                </Chip>
              ))}
            </div>
          </fieldset>

          {(
            [
              [
                "document",
                documentInput,
                document,
                setDocument,
                "environment",
                <IdentificationCard key="d" aria-hidden size={24} weight="bold" />,
              ],
              [
                "selfie",
                selfieInput,
                selfie,
                setSelfie,
                "user",
                <Camera key="s" aria-hidden size={24} weight="bold" />,
              ],
            ] as const
          ).map(([key, ref, file, setFile, capture, icon]) => (
            <div key={key} className="border-trait rounded-card flex flex-col gap-2 border p-4">
              <p className="font-bold">{t(`${key}.label`)}</p>
              <p className="text-small text-prune-doux">{t(`${key}.hint`)}</p>
              <input
                ref={ref}
                type="file"
                accept="image/*"
                capture={capture}
                className="sr-only"
                tabIndex={-1}
                aria-label={t(`${key}.label`)}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <Button variant="secondary" onClick={() => ref.current?.click()}>
                {icon}
                {file ? t("chosen", { name: file.name }) : t(`${key}.take`)}
              </Button>
            </div>
          ))}

          <p className="text-small text-prune-doux flex gap-2">
            <LockKey aria-hidden size={20} className="shrink-0" />
            {t("privacy")}
          </p>
          {error && (
            <p role="alert" className="text-alerte font-bold">
              {error}
            </p>
          )}
          <Button
            size="lg"
            fullWidth
            disabled={!document || !selfie || busy}
            onClick={() => void send()}
          >
            {t("send")}
          </Button>
        </>
      )}
    </SectionFrame>
  );
}
