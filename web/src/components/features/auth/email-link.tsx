"use client";

import { CheckCircle, LockKey, WarningCircle } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { SpeakButton } from "@/components/ui/speak-button";
import { confirmEmail, resetPassword } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { Link } from "@/lib/i18n/navigation";

import { ErrorMessage } from "./error-message";
import { PasswordField } from "./password-field";
import { useSignedIn } from "./use-signed-in";

/** The link of the confirmation e-mail: confirms at once and signs in. */
export function ConfirmEmail({ token }: { token: string }) {
  const t = useTranslations("auth.confirm");
  const signedIn = useSignedIn();
  const [failure, setFailure] = useState<string>();
  const started = useRef(false);

  useEffect(() => {
    // Once only (React runs effects twice in development): a link works one time.
    if (started.current) return;
    started.current = true;
    confirmEmail(token)
      .then(signedIn)
      .catch((err: unknown) =>
        setFailure(err instanceof ApiError && err.body.message ? err.body.message : t("error")),
      );
  }, [token, signedIn, t]);

  if (failure) {
    return (
      <section aria-labelledby="confirm-title" className="flex flex-col gap-6">
        <WarningCircle aria-hidden size={56} weight="duotone" className="text-alerte" />
        <h1 id="confirm-title" className="font-display text-headline font-black">
          {t("failedTitle")}
        </h1>
        <p role="alert" className="text-lead">
          {failure}
        </p>
        <Link
          href={{ pathname: "/auth", query: { mode: "signin" } }}
          className={buttonClasses({ size: "lg", fullWidth: true })}
        >
          {t("signIn")}
        </Link>
      </section>
    );
  }
  return (
    <section
      aria-labelledby="confirm-title"
      className="flex flex-col items-center gap-4 py-10 text-center"
    >
      <CheckCircle aria-hidden size={56} weight="duotone" className="text-feuille" />
      <h1 id="confirm-title" className="font-display text-headline font-black" role="status">
        {t("working")}
      </h1>
    </section>
  );
}

/** The link of « Forgot password »: choose a new one, then signed in. */
export function ResetPassword({ token }: { token: string }) {
  const t = useTranslations("auth.reset");
  const tAuth = useTranslations("auth");
  const signedIn = useSignedIn();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [passwordError, setPasswordError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(undefined);
    setPasswordError(undefined);
    setBusy(true);
    try {
      await signedIn(await resetPassword(token, password));
    } catch (err) {
      if (err instanceof ApiError) {
        const fields = (err.body.fields ?? {}) as Record<string, string[] | undefined>;
        if (fields.password?.length) setPasswordError(fields.password.join(" "));
        else setError(err.body.message || tAuth("errors.network"));
      } else {
        setError(tAuth("errors.network"));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="reset-title" className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-3">
        <h1 id="reset-title" className="font-display text-headline font-black">
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} />
      </div>
      <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-5" noValidate>
        <PasswordField
          label={tAuth("password.choose")}
          autoComplete="new-password"
          hint={tAuth("password.hint")}
          error={passwordError}
          value={password}
          onChange={setPassword}
        />
        <ErrorMessage message={error} />
        <Button
          type="submit"
          size="lg"
          fullWidth
          disabled={busy || password.length === 0}
          icon={<LockKey size={22} weight="bold" />}
        >
          {t("submit")}
        </Button>
      </form>
      {error && (
        <Link
          href={{ pathname: "/auth", query: { mode: "signin" } }}
          className="text-hibiscus self-start font-bold underline"
        >
          {t("again")}
        </Link>
      )}
    </section>
  );
}
