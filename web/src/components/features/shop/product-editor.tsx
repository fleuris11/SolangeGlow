"use client";

import { Camera, CheckCircle, Hourglass, Plus, Trash, VideoCamera, X } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { VoiceRecorder } from "@/components/features/pros/my/voice-recorder";
import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getMedia } from "@/lib/api/payments";
import {
  createProduct,
  getCategories,
  getMyProduct,
  getMyShop,
  publishProduct,
  updateProduct,
  uploadShopMedia,
  type MyProduct,
  type VariantInput,
} from "@/lib/api/shop";
import { cn } from "@/lib/cn";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { mediaSrc, type Media } from "@/lib/media";
import { moneyInput, parseMoney } from "@/lib/money";

type Purpose = "product_photo" | "product_video" | "product_voice";
type Kind = "none" | "shade" | "size" | "color";
type Row = { id?: string; name: string; swatch: string; price: string; stock: string };

/** Sends a file and waits until it is prepared (pictures, video, voice). */
async function send(file: Blob, purpose: Purpose, name?: string): Promise<Media> {
  const sent = await uploadShopMedia(file, purpose, name);
  for (let attempt = 0; attempt < 80; attempt++) {
    const media = await getMedia(sent.id);
    if (media.status === "ready") return media;
    if (media.status === "rejected" || media.status === "failed") {
      throw new Error(media.error || "refused");
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error("timeout");
}

function kindOf(product: MyProduct | undefined): Kind {
  const first = product?.variants[0];
  if (!first || !first.label) return "none";
  if (first.shade) return "shade";
  if (first.size) return "size";
  return "color";
}

function rowsOf(product: MyProduct | undefined, currency: string, locale: string): Row[] {
  if (!product) return [{ name: "", swatch: "", price: "", stock: "1" }];
  return product.variants.map((v) => ({
    id: v.id,
    name: v.shade || v.size || v.color,
    swatch: v.swatch,
    price: v.own_price_minor !== null ? moneyInput(v.own_price_minor, currency, locale) : "",
    stock: String(v.stock),
  }));
}

function Editor({ product, currency }: { product?: MyProduct; currency: string }) {
  const t = useTranslations("shop.editor");
  const tStatus = useTranslations("shop.productStatus");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const categories = useQuery({ queryKey: ["shop-categories"], queryFn: getCategories });
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [photos, setPhotos] = useState<Media[]>(product?.photos ?? []);
  const [video, setVideo] = useState<Media | null>(product?.video ?? null);
  const [voice, setVoice] = useState<Media | null>(product?.description_voice ?? null);
  const [title, setTitle] = useState(product?.title ?? "");
  const [category, setCategory] = useState(product?.category?.key ?? "");
  const [price, setPrice] = useState(
    product ? moneyInput(product.base_price_minor, currency, locale) : "",
  );
  const [prep, setPrep] = useState(String(product?.prep_days ?? 1));
  const [description, setDescription] = useState(product?.description ?? "");
  const [kind, setKind] = useState<Kind>(kindOf(product));
  const [rows, setRows] = useState<Row[]>(rowsOf(product, currency, locale));
  const [result, setResult] = useState<MyProduct | null>(null);
  const photoInput = useRef<HTMLInputElement>(null);
  const videoInput = useRef<HTMLInputElement>(null);

  const upload = async (files: Blob[], purpose: Purpose, name?: string) => {
    setBusy(true);
    try {
      const sent = await Promise.all(files.map((file) => send(file, purpose, name)));
      if (purpose === "product_photo") setPhotos((current) => [...current, ...sent].slice(0, 8));
      if (purpose === "product_video") setVideo(sent[0] ?? null);
      if (purpose === "product_voice") setVoice(sent[0] ?? null);
      toast(t("sent"), "success");
    } catch {
      toast(t("mediaError"), "warning");
    } finally {
      setBusy(false);
    }
  };

  const variants = (): VariantInput[] =>
    (kind === "none" ? rows.slice(0, 1) : rows).map((row) => ({
      id: row.id ?? null,
      shade: kind === "shade" ? row.name.trim() : "",
      swatch: kind === "shade" ? row.swatch : "",
      size: kind === "size" ? row.name.trim() : "",
      color: kind === "color" ? row.name.trim() : "",
      price_minor: kind !== "none" && row.price ? parseMoney(row.price, currency) : null,
      stock: Number(row.stock || 0),
    }));

  const save = async (publish: boolean) => {
    const amount = parseMoney(price, currency);
    if (amount === null || amount < 1) {
      toast(t("priceNeeded"), "warning");
      setStep(2);
      return;
    }
    setBusy(true);
    try {
      const body = {
        title,
        price_minor: amount,
        category: category || null,
        description,
        prep_days: Number(prep || 0),
        photos: photos.map((p) => p.id),
        video: video?.id ?? null,
        voice: voice?.id ?? null,
        variants: variants(),
      };
      let saved = product ? await updateProduct(product.id, body) : await createProduct(body);
      if (publish && (saved.status === "draft" || saved.status === "paused")) {
        saved = await publishProduct(saved.id);
      }
      await queryClient.invalidateQueries({ queryKey: ["my-products"] });
      if (publish) setResult(saved);
      else {
        toast(t("draftSaved"), "success");
        router.push("/pro/shop");
      }
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  if (result) {
    const online = result.status === "published";
    return (
      <section
        className="flex flex-col items-center gap-5 py-8 text-center"
        aria-labelledby="result"
      >
        {online ? (
          <Bloom label={t("online")} size={140} />
        ) : (
          <Hourglass aria-hidden size={72} weight="duotone" className="text-or" />
        )}
        <h1 id="result" className="font-display text-display font-black">
          {online ? t("online") : tStatus(result.status)}
        </h1>
        <p className="text-lead max-w-[34ch]">{online ? t("onlineHelp") : t("reviewHelp")}</p>
        <Link href="/pro/shop" className={buttonClasses({ size: "lg", fullWidth: true })}>
          {t("backToShop")}
        </Link>
        {online && result.shop_slug && (
          <Link
            href={`/${result.shop_slug}/shop/${result.slug}`}
            className="text-hibiscus font-bold underline"
          >
            {t("see")}
          </Link>
        )}
      </section>
    );
  }

  const titles = [t("step1"), t("step2"), t("step3"), t("step4")];
  const canNext =
    (step === 1 && photos.length > 0) ||
    (step === 2 && title.trim() && category && parseMoney(price, currency)) ||
    step === 3;

  return (
    <div className="flex flex-col gap-6">
      <Stepper current={step} total={4} onBack={() => setStep(step - 1)} />
      <h1 className="text-headline font-bold">{titles[step - 1]}</h1>

      {step === 1 && (
        <div className="flex flex-col gap-4">
          <p className="text-prune-doux">{t("photosHelp")}</p>
          <ul className="grid grid-cols-3 gap-2">
            {photos.map((photo, index) => (
              <li key={photo.id} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
                <img
                  src={mediaSrc(photo, "thumb", "medium")}
                  alt={t("photoN", { n: index + 1 })}
                  className="aspect-square w-full rounded-xl object-cover"
                />
                <button
                  type="button"
                  aria-label={t("removePhoto", { n: index + 1 })}
                  onClick={() => setPhotos(photos.filter((p) => p.id !== photo.id))}
                  className="bg-carte absolute top-1 right-1 inline-flex size-12 items-center justify-center rounded-full"
                >
                  <X aria-hidden size={20} weight="bold" />
                </button>
              </li>
            ))}
          </ul>
          <input
            ref={photoInput}
            type="file"
            accept="image/*"
            multiple
            className="sr-only"
            tabIndex={-1}
            aria-label={t("addPhotos")}
            onChange={(event) => {
              const files = Array.from(event.target.files ?? []);
              event.target.value = "";
              if (files.length) void upload(files, "product_photo");
            }}
          />
          <Button
            variant="secondary"
            size="lg"
            disabled={busy || photos.length >= 8}
            onClick={() => photoInput.current?.click()}
          >
            <Camera aria-hidden size={24} weight="bold" />
            {t("addPhotos")}
          </Button>
          <input
            ref={videoInput}
            type="file"
            accept="video/*"
            className="sr-only"
            tabIndex={-1}
            aria-label={t("addVideo")}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) void upload([file], "product_video");
            }}
          />
          <Button variant="quiet" disabled={busy} onClick={() => videoInput.current?.click()}>
            <VideoCamera aria-hidden size={22} weight="bold" />
            {video ? t("videoOk") : t("addVideo")}
          </Button>
          {busy && <p role="status">{t("sending")}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-4">
          <Input
            label={t("title")}
            required
            value={title}
            maxLength={120}
            onChange={(e) => setTitle(e.target.value)}
          />
          <label className="flex flex-col gap-2 font-bold">
            {t("category")}
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-field bg-poudre min-h-14 px-4"
            >
              <option value="">{t("chooseCategory")}</option>
              {(categories.data ?? []).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <Input
            label={t("price", { currency })}
            inputMode="decimal"
            required
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            hint={t("priceHelp")}
          />
          <Input
            label={t("prep")}
            inputMode="numeric"
            value={prep}
            onChange={(e) => setPrep(e.target.value.replace(/\D/g, ""))}
            hint={t("prepHelp")}
          />
          <label htmlFor="product-description" className="font-bold">
            {t("description")}
          </label>
          <textarea
            id="product-description"
            rows={4}
            maxLength={3000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="rounded-field bg-poudre focus:border-hibiscus w-full border-2 border-transparent px-4 py-3 outline-none"
          />
          <div className="flex flex-col gap-2">
            <p className="font-bold">{t("voice")}</p>
            <p className="text-small text-prune-doux">{voice ? t("voiceOk") : t("voiceHelp")}</p>
            <VoiceRecorder
              onRecorded={(file) => void upload([file], "product_voice", "description.webm")}
            />
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="flex flex-col gap-4">
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("choices")}</legend>
            <div className="flex flex-wrap gap-2">
              {(["none", "shade", "size", "color"] as const).map((option) => (
                <label
                  key={option}
                  className={cn(
                    "flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold",
                    kind === option ? "border-hibiscus bg-poudre" : "border-trait",
                  )}
                >
                  <input
                    type="radio"
                    name="variant-kind"
                    className="sr-only"
                    checked={kind === option}
                    onChange={() => setKind(option)}
                  />
                  {t(`kind.${option}`)}
                </label>
              ))}
            </div>
          </fieldset>
          {kind === "none" ? (
            <Input
              label={t("stock")}
              inputMode="numeric"
              value={rows[0]?.stock ?? "0"}
              onChange={(e) =>
                setRows([
                  {
                    ...(rows[0] ?? { name: "", swatch: "", price: "" }),
                    stock: e.target.value.replace(/\D/g, ""),
                  },
                ])
              }
            />
          ) : (
            <>
              <ul className="flex flex-col gap-3">
                {rows.map((row, index) => {
                  const update = (change: Partial<Row>) =>
                    setRows(rows.map((r, i) => (i === index ? { ...r, ...change } : r)));
                  return (
                    <li
                      key={row.id ?? index}
                      className="border-trait rounded-card flex flex-col gap-3 border p-3"
                    >
                      <Input
                        label={t(`name.${kind}`)}
                        value={row.name}
                        maxLength={60}
                        onChange={(e) => update({ name: e.target.value })}
                      />
                      {kind === "shade" && (
                        <label className="flex min-h-12 items-center gap-3 font-bold">
                          <input
                            type="color"
                            value={row.swatch || "#a0522d"}
                            onChange={(e) => update({ swatch: e.target.value })}
                            className="size-12 rounded-full"
                          />
                          {t("swatch")}
                        </label>
                      )}
                      <div className="grid grid-cols-2 gap-3">
                        <Input
                          label={t("stock")}
                          inputMode="numeric"
                          value={row.stock}
                          onChange={(e) => update({ stock: e.target.value.replace(/\D/g, "") })}
                        />
                        <Input
                          label={t("ownPrice")}
                          inputMode="decimal"
                          value={row.price}
                          onChange={(e) => update({ price: e.target.value })}
                        />
                      </div>
                      {rows.length > 1 && (
                        <Button
                          variant="quiet"
                          onClick={() => setRows(rows.filter((_, i) => i !== index))}
                        >
                          <Trash aria-hidden size={20} />
                          {t("removeChoice")}
                        </Button>
                      )}
                    </li>
                  );
                })}
              </ul>
              <Button
                variant="secondary"
                onClick={() => setRows([...rows, { name: "", swatch: "", price: "", stock: "1" }])}
              >
                <Plus aria-hidden size={20} weight="bold" />
                {t("addChoice")}
              </Button>
            </>
          )}
        </div>
      )}

      {step === 4 && (
        <div className="flex flex-col gap-4">
          <ul className="flex flex-col gap-2">
            {[
              [photos.length > 0, t("checkPhotos", { count: photos.length })],
              [Boolean(title && category), t("checkInfo")],
              [true, t("checkChoices", { count: kind === "none" ? 1 : rows.length })],
            ].map(([ok, text]) => (
              <li key={String(text)} className="flex items-center gap-2">
                <CheckCircle
                  aria-hidden
                  size={22}
                  weight="fill"
                  className={ok ? "text-feuille" : "text-prune-doux"}
                />
                {text}
              </li>
            ))}
          </ul>
          <p className="bg-poudre rounded-2xl p-3">{t("checkWords")}</p>
          <Button size="lg" fullWidth disabled={busy} onClick={() => void save(true)}>
            {t("publish")}
          </Button>
          <Button variant="secondary" fullWidth disabled={busy} onClick={() => void save(false)}>
            {t("draft")}
          </Button>
        </div>
      )}

      {step < 4 && (
        <Button size="lg" fullWidth disabled={!canNext || busy} onClick={() => setStep(step + 1)}>
          {t("next")}
        </Button>
      )}
    </div>
  );
}

/** Create (« new ») or change a product, in 4 steps. */
export function ProductEditor({ productId }: { productId: string }) {
  const shop = useQuery({ queryKey: ["my-shop"], queryFn: getMyShop, retry: false });
  const existing = useQuery({
    queryKey: ["my-product", productId],
    queryFn: () => getMyProduct(productId),
    enabled: productId !== "new",
  });
  if (shop.isPending || (productId !== "new" && existing.isPending)) {
    return <Skeleton className="rounded-card h-80" />;
  }
  if (!shop.data) return null;
  return (
    <Editor
      key={existing.data?.id ?? "new"}
      product={existing.data}
      currency={shop.data.currency}
    />
  );
}
