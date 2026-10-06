"use client";

import { Camera, CircleNotch, Trash, User, WarningCircle } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorMessage } from "@/components/features/auth/error-message";
import { Avatar } from "@/components/ui/avatar";
import { BlurPreview } from "@/components/ui/blur-preview";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { getCountries, removePhoto, updateMe, uploadPhoto, type Me } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { useSetMe } from "@/lib/auth/use-me";
import { zodResolver } from "@/lib/forms/zod-resolver";
import { routing } from "@/lib/i18n/routing";

import { ContactChange } from "./contact-change";

const CURRENCIES = ["XOF", "EUR"] as const;

const schema = z.object({
  first_name: z.string().trim().max(150),
  last_name: z.string().trim().max(150),
  city: z.string().trim().max(80),
  country: z.string(),
  preferred_language: z.enum(routing.locales),
  preferred_currency: z.enum(CURRENCIES),
});

type Values = z.infer<typeof schema>;

const selectClass =
  "rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 outline-none";

/** Photo (petal), name, city, country, language and currency. */
export function ProfileForm({ me }: { me: Me }) {
  const t = useTranslations("profile");
  const tLocales = useTranslations("locales");
  const toast = useToast();
  const setMe = useSetMe();
  const fileInput = useRef<HTMLInputElement>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [error, setError] = useState<string>();
  const countries = useQuery({ queryKey: ["countries"], queryFn: getCountries });

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: me.first_name,
      last_name: me.last_name,
      city: me.city,
      country: me.country ?? "",
      preferred_language: me.preferred_language,
      preferred_currency: (me.preferred_currency as Values["preferred_currency"]) ?? "XOF",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setError(undefined);
    try {
      const updated = await updateMe({ ...values, country: values.country || null });
      setMe(updated);
      form.reset(values);
      toast(t("saved"));
    } catch (err) {
      setError(err instanceof ApiError && err.body.message ? err.body.message : t("error"));
    }
  });

  const onPhoto = async (file: File | undefined) => {
    if (!file) return;
    setError(undefined);
    setPhotoBusy(true);
    try {
      setMe(await uploadPhoto(file));
      toast(t("photoSaved"));
    } catch (err) {
      setError(err instanceof ApiError && err.body.message ? err.body.message : t("error"));
    } finally {
      setPhotoBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const displayName = [me.first_name, me.last_name].filter(Boolean).join(" ") || t("noName");
  const photo = me.photo;
  const photoReady = photo?.status === "ready";
  const photoProcessing = photo?.status === "pending" || photo?.status === "processing";
  const photoUrl = photoReady ? (photo.urls.medium ?? photo.urls.large) : undefined;
  const hasName = !!(me.first_name || me.last_name);
  // While the photo is prepared (a few seconds), its blurred preview stands in.
  const picture =
    photoProcessing && photo?.blurhash ? (
      <BlurPreview hash={photo.blurhash} />
    ) : hasName ? undefined : (
      <span className="flex size-full items-center justify-center">
        <User size={64} weight="duotone" />
      </span>
    );

  return (
    <section aria-labelledby="profile-title" className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Avatar name={displayName} src={photoUrl} size="xl" picture={picture} />
        <div className="flex min-w-0 flex-col gap-2">
          <h2 id="profile-title" className="font-display text-headline font-black break-words">
            {displayName}
          </h2>
          <p className="text-prune-doux">{me.phone ?? me.email}</p>
        </div>
      </div>

      {photoProcessing && (
        <p role="status" className="text-small text-prune-doux flex items-center gap-2">
          <CircleNotch aria-hidden size={20} className="animate-spin motion-reduce:animate-none" />
          {t("photoProcessing")}
        </p>
      )}
      {photo && (photo.status === "rejected" || photo.status === "failed") && (
        <p role="alert" className="text-small text-alerte flex items-start gap-2 font-bold">
          <WarningCircle aria-hidden size={20} weight="fill" className="mt-0.5 shrink-0" />
          {t("photoRejected")}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <input
          ref={fileInput}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          id="avatar-file"
          tabIndex={-1}
          aria-label={photo ? t("changePhoto") : t("addPhoto")}
          onChange={(event) => void onPhoto(event.target.files?.[0])}
        />
        <Button
          variant="secondary"
          icon={<Camera size={22} weight="duotone" />}
          disabled={photoBusy}
          onClick={() => fileInput.current?.click()}
        >
          {photo ? t("changePhoto") : t("addPhoto")}
        </Button>
        {photo && (
          <Button
            variant="quiet"
            icon={<Trash size={22} weight="duotone" />}
            disabled={photoBusy}
            onClick={async () => setMe(await removePhoto())}
          >
            {t("removePhoto")}
          </Button>
        )}
      </div>

      <ContactChange me={me} />

      <form onSubmit={onSubmit} className="flex flex-col gap-5" noValidate>
        <Input label={t("firstName")} autoComplete="given-name" {...form.register("first_name")} />
        <Input label={t("lastName")} autoComplete="family-name" {...form.register("last_name")} />
        <Input label={t("city")} autoComplete="address-level2" {...form.register("city")} />

        <div className="flex flex-col gap-2">
          <label htmlFor="profile-country" className="font-bold">
            {t("country")}
          </label>
          <select id="profile-country" className={selectClass} {...form.register("country")}>
            <option value="">{t("countryNone")}</option>
            {countries.data?.map((country) => (
              <option key={country.code} value={country.code}>
                {country.name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <label htmlFor="profile-language" className="font-bold">
              {t("language")}
            </label>
            <select
              id="profile-language"
              className={selectClass}
              {...form.register("preferred_language")}
            >
              {routing.locales.map((code) => (
                <option key={code} value={code} lang={code}>
                  {tLocales(code)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="profile-currency" className="font-bold">
              {t("currency")}
            </label>
            <select
              id="profile-currency"
              className={selectClass}
              {...form.register("preferred_currency")}
            >
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {t(`currencies.${code}`)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <ErrorMessage message={error} />

        <Button type="submit" size="lg" fullWidth disabled={form.formState.isSubmitting}>
          {t("save")}
        </Button>
      </form>
    </section>
  );
}
