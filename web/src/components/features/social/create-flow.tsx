"use client";

import { CircleNotch, Plus, UploadSimple, WarningCircle } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { TradeIcon, TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getMyPro } from "@/lib/api/pros";
import {
  createPost,
  createStory,
  getMedia,
  uploadMedia,
  type PostInput,
  type StoryInput,
} from "@/lib/api/social";
import { useMe } from "@/lib/auth/use-me";
import { useRouter } from "@/lib/i18n/navigation";
import { mediaSrc, type Media } from "@/lib/media";

type Kind =
  "photo" | "carousel" | "video" | "before_after" | "story_photo" | "story_text" | "free_slots";
type Upload = { key: string; role: "item" | "before" | "after"; media?: Media; error?: string };

const POST_KINDS: Kind[] = ["photo", "carousel", "video", "before_after"];
const STORY_KINDS: Kind[] = ["story_photo", "story_text", "free_slots"];
const BACKGROUNDS = ["hibiscus", "prune", "or", "feuille", "poudre"] as const;
const COLOURS: Record<string, string> = {
  hibiscus: "bg-hibiscus text-sur-hibiscus",
  prune: "bg-prune text-lait",
  or: "bg-or text-sur-or",
  feuille: "bg-feuille text-lait",
  poudre: "bg-poudre text-prune",
};

function slotsFrom(now = new Date()): string[] {
  const slots: string[] = [];
  for (let hour = Math.max(now.getHours() + 1, 8); hour <= 20; hour++) {
    slots.push(`${String(hour).padStart(2, "0")}:00`, `${String(hour).padStart(2, "0")}:30`);
  }
  return slots;
}

async function waitReady(id: string): Promise<Media> {
  for (let attempt = 0; attempt < 90; attempt++) {
    const media = await getMedia(id);
    if (media.status === "ready" || media.status === "rejected" || media.status === "failed") {
      return media;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  return getMedia(id);
}

/** « Publier »: what (and the files), the words, then preview and publish. */
export function CreateFlow() {
  const t = useTranslations("social.create");
  const tTrades = useTranslations("trades");
  const toast = useToast();
  const router = useRouter();
  const me = useMe();
  const isPro = me.data?.roles.includes("pro") ?? false;
  const pro = useQuery({ queryKey: ["me", "pro"], queryFn: getMyPro, enabled: isPro });

  const [step, setStep] = useState(1);
  const [kind, setKind] = useState<Kind | null>(null);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [caption, setCaption] = useState("");
  const [trade, setTrade] = useState<string>("");
  const [serviceId, setServiceId] = useState("");
  const [text, setText] = useState("");
  const [background, setBackground] = useState<(typeof BACKGROUNDS)[number]>("hibiscus");
  const [slots, setSlots] = useState<string[]>([]);
  const [when, setWhen] = useState<"now" | "later" | "draft">("now");
  const [publishAt, setPublishAt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const fileInput = useRef<HTMLInputElement>(null);
  const role = useRef<Upload["role"]>("item");

  const isStory = kind !== null && STORY_KINDS.includes(kind);
  const purpose = isStory ? "story" : "post";
  const accept =
    kind === "video" ? "video/*" : kind === "story_photo" ? "image/*,video/*" : "image/*";
  const ready = uploads.filter((u) => u.media?.status === "ready");
  const waiting = uploads.some((u) => !u.media && !u.error);

  const pick = (wanted: Upload["role"]) => {
    role.current = wanted;
    fileInput.current?.click();
  };

  const addFiles = async (files: FileList | null) => {
    for (const file of Array.from(files ?? [])) {
      const key = `${file.name}-${Math.random()}`;
      const entry: Upload = { key, role: role.current };
      setUploads((current) => [
        ...current.filter((u) => role.current === "item" || u.role !== role.current),
        entry,
      ]);
      try {
        const sent = await uploadMedia(file, purpose);
        const media = await waitReady(sent.id);
        setUploads((current) =>
          current.map((u) =>
            u.key === key
              ? media.status === "ready"
                ? { ...u, media }
                : { ...u, error: t("refused") }
              : u,
          ),
        );
      } catch (failure) {
        const message = failure instanceof ApiError ? failure.message : t("uploadError");
        setUploads((current) => current.map((u) => (u.key === key ? { ...u, error: message } : u)));
      }
    }
  };

  const mediaOk =
    kind === "photo" || kind === "video" || kind === "story_photo"
      ? ready.length === 1
      : kind === "carousel"
        ? ready.length >= 2
        : kind === "before_after"
          ? ready.some((u) => u.role === "before") && ready.some((u) => u.role === "after")
          : true;
  const canContinue =
    (step === 1 && kind !== null && mediaOk && !waiting) ||
    (step === 2 &&
      (kind === "story_text"
        ? text.trim().length > 0
        : kind === "free_slots"
          ? slots.length > 0
          : true)) ||
    step === 3;

  const publish = async () => {
    if (!kind) return;
    setBusy(true);
    setError(undefined);
    try {
      if (isStory) {
        const body: StoryInput =
          kind === "free_slots"
            ? { kind: "free_slots", slots }
            : kind === "story_text"
              ? { kind: "text", text, background }
              : {
                  kind: ready[0]?.media?.kind === "video" ? "video" : "photo",
                  media_id: ready[0]?.media?.id,
                  text,
                };
        await createStory(body);
        toast(t("storyDone"), "success");
        router.push("/");
      } else {
        const body: PostInput = {
          kind: kind as PostInput["kind"],
          media: ready.map((u) => ({ id: u.media!.id, role: u.role })),
          caption,
          trade: trade || null,
          service_id: serviceId || null,
          status: when === "now" ? "published" : when === "later" ? "scheduled" : "draft",
          publish_at: when === "later" && publishAt ? new Date(publishAt).toISOString() : null,
        };
        const post = await createPost(body);
        toast(
          when === "now" ? t("published") : when === "later" ? t("scheduled") : t("drafted"),
          "success",
        );
        router.push(when === "now" ? `/p/${post.id}` : "/me/posts");
      }
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
      setBusy(false);
    }
  };

  const titles = [t("steps.what"), t("steps.details"), t("steps.publish")];
  const helps = [t("help.what"), t("help.details"), t("help.publish")];
  const kinds = [...POST_KINDS, ...STORY_KINDS.filter((k) => k !== "free_slots" || isPro)];

  return (
    <div className="flex flex-col gap-6">
      <Stepper current={step} total={3} onBack={() => setStep(step - 1)} />
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline font-bold">{titles[step - 1]}</h1>
          <p className="text-prune-doux">{helps[step - 1]}</p>
        </div>
        <SpeakButton text={`${titles[step - 1]}. ${helps[step - 1]}`} />
      </div>

      <input
        ref={fileInput}
        type="file"
        accept={accept}
        multiple={kind === "carousel"}
        className="sr-only"
        tabIndex={-1}
        aria-label={t("choose")}
        onChange={(event) => {
          void addFiles(event.target.files);
          event.target.value = "";
        }}
      />

      {step === 1 && (
        <>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("post")}</legend>
            <div className="flex flex-wrap gap-2">
              {kinds
                .filter((k) => POST_KINDS.includes(k))
                .map((k) => (
                  <Chip key={k} selected={kind === k} onClick={() => (setKind(k), setUploads([]))}>
                    {t(`kinds.${k}`)}
                  </Chip>
                ))}
            </div>
          </fieldset>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("story")}</legend>
            <div className="flex flex-wrap gap-2">
              {kinds
                .filter((k) => STORY_KINDS.includes(k))
                .map((k) => (
                  <Chip key={k} selected={kind === k} onClick={() => (setKind(k), setUploads([]))}>
                    {t(`kinds.${k}`)}
                  </Chip>
                ))}
            </div>
          </fieldset>

          {kind && kind !== "story_text" && kind !== "free_slots" && (
            <div className="flex flex-col gap-3">
              {kind === "before_after" ? (
                <div className="grid grid-cols-2 gap-3">
                  <Button variant="secondary" onClick={() => pick("before")}>
                    <UploadSimple aria-hidden size={22} weight="bold" />
                    {t("before")}
                  </Button>
                  <Button variant="secondary" onClick={() => pick("after")}>
                    <UploadSimple aria-hidden size={22} weight="bold" />
                    {t("after")}
                  </Button>
                </div>
              ) : (
                <Button variant="secondary" onClick={() => pick("item")}>
                  {kind === "carousel" && uploads.length ? (
                    <Plus aria-hidden size={22} weight="bold" />
                  ) : (
                    <UploadSimple aria-hidden size={22} weight="bold" />
                  )}
                  {kind === "carousel" && uploads.length ? t("addMore") : t("choose")}
                </Button>
              )}
              <ul className="grid grid-cols-3 gap-2">
                {uploads.map((upload) => (
                  <li
                    key={upload.key}
                    className="bg-poudre relative flex aspect-square items-center justify-center overflow-hidden rounded-2xl"
                  >
                    {upload.media ? (
                      // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                      <img
                        src={mediaSrc(upload.media, "thumb", "medium")}
                        alt=""
                        className="size-full object-cover"
                      />
                    ) : upload.error ? (
                      <span className="text-alerte text-mention flex flex-col items-center gap-1 p-2 text-center font-bold">
                        <WarningCircle aria-hidden size={22} weight="fill" />
                        {upload.error}
                      </span>
                    ) : (
                      <span className="text-mention flex flex-col items-center gap-1" role="status">
                        <CircleNotch aria-hidden size={22} className="animate-spin" />
                        {t("preparing")}
                      </span>
                    )}
                    {upload.role !== "item" && (
                      <span className="bg-carte text-mention absolute top-1 left-1 rounded-full px-2 font-bold">
                        {t(upload.role)}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {step === 2 && !isStory && (
        <>
          <div className="flex flex-col gap-2">
            <label htmlFor="caption" className="font-bold">
              {t("caption")}
            </label>
            <textarea
              id="caption"
              rows={4}
              maxLength={2200}
              placeholder={t("captionPlaceholder")}
              value={caption}
              onChange={(event) => setCaption(event.target.value)}
              className="rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 py-3 outline-none"
            />
          </div>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("trade")}</legend>
            <div className="flex flex-wrap gap-2">
              {TRADES.map((key: Trade) => (
                <Chip
                  key={key}
                  selected={trade === key}
                  icon={<TradeIcon trade={key} size={22} />}
                  onClick={() => setTrade(trade === key ? "" : key)}
                >
                  {tTrades(key)}
                </Chip>
              ))}
            </div>
          </fieldset>
          {isPro && (pro.data?.services.length ?? 0) > 0 && (
            <div className="flex flex-col gap-2">
              <label htmlFor="service" className="font-bold">
                {t("service")}
              </label>
              <select
                id="service"
                value={serviceId}
                onChange={(event) => setServiceId(event.target.value)}
                className="rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 outline-none"
              >
                <option value="">{t("noService")}</option>
                {pro.data?.services.map((service) => (
                  <option key={service.id} value={service.id}>
                    {service.name}
                  </option>
                ))}
              </select>
              <p className="text-small text-prune-doux">{t("serviceHelp")}</p>
            </div>
          )}
        </>
      )}

      {step === 2 && kind === "story_text" && (
        <>
          <Input
            label={t("storyText")}
            value={text}
            maxLength={200}
            onChange={(e) => setText(e.target.value)}
          />
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("background")}</legend>
            <div className="flex flex-wrap gap-2">
              {BACKGROUNDS.map((colour) => (
                <Chip
                  key={colour}
                  selected={background === colour}
                  onClick={() => setBackground(colour)}
                >
                  {t(`colours.${colour}`)}
                </Chip>
              ))}
            </div>
          </fieldset>
        </>
      )}

      {step === 2 && kind === "free_slots" && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-bold">{t("slots")}</legend>
          <div className="flex flex-wrap gap-2">
            {slotsFrom().map((slot) => (
              <Chip
                key={slot}
                selected={slots.includes(slot)}
                onClick={() =>
                  setSlots(
                    slots.includes(slot) ? slots.filter((s) => s !== slot) : [...slots, slot],
                  )
                }
              >
                {slot}
              </Chip>
            ))}
          </div>
        </fieldset>
      )}

      {step === 2 && kind === "story_photo" && (
        <Input
          label={t("storyCaption")}
          value={text}
          maxLength={200}
          onChange={(e) => setText(e.target.value)}
        />
      )}

      {step === 3 && (
        <>
          <div className="border-trait rounded-card flex flex-col gap-3 overflow-hidden border">
            <p className="text-small text-prune-doux px-4 pt-4 font-bold">{t("preview")}</p>
            {kind === "story_text" ? (
              <p
                className={`font-display text-headline flex min-h-48 items-center justify-center p-6 text-center font-black ${COLOURS[background]}`}
              >
                {text}
              </p>
            ) : kind === "free_slots" ? (
              <p className="px-4 pb-4 font-bold">
                {t("slotsPreview", { slots: [...slots].sort().join(", ") })}
              </p>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-1">
                  {ready.map((upload) => (
                    // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                    <img
                      key={upload.key}
                      src={mediaSrc(upload.media, "medium", "thumb")}
                      alt=""
                      className="aspect-[4/5] w-full object-cover"
                    />
                  ))}
                </div>
                {(caption || text) && <p className="px-4 pb-4">{caption || text}</p>}
              </>
            )}
          </div>
          {!isStory && (
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-2 font-bold">{t("when")}</legend>
              <div className="flex flex-wrap gap-2">
                {(["now", "later", "draft"] as const).map((option) => (
                  <Chip key={option} selected={when === option} onClick={() => setWhen(option)}>
                    {t(`whenOptions.${option}`)}
                  </Chip>
                ))}
              </div>
              {when === "later" && (
                <Input
                  type="datetime-local"
                  label={t("publishAt")}
                  value={publishAt}
                  onChange={(event) => setPublishAt(event.target.value)}
                />
              )}
            </fieldset>
          )}
        </>
      )}

      {error && (
        <p role="alert" className="text-alerte font-bold">
          {error}
        </p>
      )}
      <Button
        size="lg"
        fullWidth
        disabled={!canContinue || busy || (step === 3 && when === "later" && !publishAt)}
        onClick={() => (step < 3 ? setStep(step + 1) : void publish())}
      >
        {step < 3
          ? t("next")
          : isStory
            ? t("publishStory")
            : when === "now"
              ? t("publishNow")
              : when === "later"
                ? t("schedule")
                : t("saveDraft")}
      </Button>
    </div>
  );
}
