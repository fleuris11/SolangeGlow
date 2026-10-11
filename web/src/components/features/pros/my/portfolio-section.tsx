"use client";

import { CircleNotch, Images, Trash, UploadSimple } from "@phosphor-icons/react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { addPortfolioItem, deletePortfolioItem, myProQueryKey, type MyPro } from "@/lib/api/pros";
import { mediaSrc } from "@/lib/media";

import { fieldClass, SectionFrame } from "./section-frame";

/** Her work: pictures or videos, optionally a « before » picture, linked to a service. */
export function PortfolioSection({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.portfolio");
  const toast = useToast();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const beforeInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [before, setBefore] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const refresh = () => queryClient.invalidateQueries({ queryKey: myProQueryKey });

  const send = async () => {
    if (!file) return;
    setBusy(true);
    setError(undefined);
    try {
      await addPortfolioItem({ file, before, caption, serviceId: serviceId || null });
      setFile(null);
      setBefore(null);
      setCaption("");
      setServiceId("");
      await refresh();
      toast(t("added"), "success");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <div className="bg-poudre rounded-card flex flex-col gap-4 p-4">
        <input
          ref={fileInput}
          type="file"
          accept="image/*,video/*"
          className="sr-only"
          tabIndex={-1}
          aria-label={t("chooseResult")}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <input
          ref={beforeInput}
          type="file"
          accept="image/*"
          className="sr-only"
          tabIndex={-1}
          aria-label={t("chooseBefore")}
          onChange={(event) => setBefore(event.target.files?.[0] ?? null)}
        />
        <Button variant="secondary" onClick={() => fileInput.current?.click()}>
          <UploadSimple aria-hidden size={22} weight="bold" />
          {file ? t("resultChosen", { name: file.name }) : t("chooseResult")}
        </Button>
        <Button variant="quiet" onClick={() => beforeInput.current?.click()}>
          <Images aria-hidden size={22} />
          {before ? t("beforeChosen", { name: before.name }) : t("chooseBefore")}
        </Button>
        <Input
          label={t("caption")}
          placeholder={t("captionPlaceholder")}
          value={caption}
          maxLength={200}
          onChange={(event) => setCaption(event.target.value)}
        />
        {pro.services.length > 0 && (
          <div className="flex flex-col gap-2">
            <label htmlFor="portfolio-service" className="font-bold">
              {t("service")}
            </label>
            <select
              id="portfolio-service"
              value={serviceId}
              onChange={(event) => setServiceId(event.target.value)}
              className={fieldClass}
            >
              <option value="">{t("noService")}</option>
              {pro.services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name}
                </option>
              ))}
            </select>
          </div>
        )}
        {error && (
          <p role="alert" className="text-alerte font-bold">
            {error}
          </p>
        )}
        <Button size="lg" fullWidth disabled={!file || busy} onClick={() => void send()}>
          {busy ? <CircleNotch aria-hidden size={22} className="animate-spin" /> : null}
          {t("add")}
        </Button>
      </div>

      {pro.portfolio.length === 0 ? (
        <p className="text-prune-doux">{t("empty")}</p>
      ) : (
        <ul className="grid grid-cols-2 gap-3">
          {pro.portfolio.map((item) => {
            const src = mediaSrc(item.media, "thumb", "medium");
            const waiting = item.media.status === "pending" || item.media.status === "processing";
            return (
              <li key={item.id} className="flex flex-col gap-2">
                <div className="bg-poudre relative flex aspect-square items-center justify-center overflow-hidden rounded-2xl">
                  {src ? (
                    // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                    <img src={src} alt={item.caption} className="size-full object-cover" />
                  ) : (
                    <span className="text-small p-2 text-center">
                      {waiting ? t("processing") : t("refused")}
                    </span>
                  )}
                  {item.before && (
                    <span className="bg-carte text-mention absolute top-2 left-2 rounded-full px-2 py-1 font-bold">
                      {t("pair")}
                    </span>
                  )}
                </div>
                {item.caption && <p className="text-small">{item.caption}</p>}
                <Button
                  variant="quiet"
                  onClick={async () => {
                    await deletePortfolioItem(item.id);
                    await refresh();
                  }}
                >
                  <Trash aria-hidden size={20} />
                  {t("remove")}
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </SectionFrame>
  );
}
