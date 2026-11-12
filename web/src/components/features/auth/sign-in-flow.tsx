"use client";

import { ArrowLeft, EnvelopeSimple, SignIn as SignInIcon, UserPlus } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SpeakButton } from "@/components/ui/speak-button";
import { forgotPassword, loginWithPassword, resendConfirmation, signUp } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/cn";

import { ErrorMessage } from "./error-message";
import { PasswordField } from "./password-field";
import { useCountdown } from "./use-countdown";
import { useSignedIn } from "./use-signed-in";

type View = "signin" | "signup" | "forgot" | "checkMail" | "resetSent";

const RESEND_SECONDS = 60;

/**
 * The classic way, on one screen: « Sign in » or « Create my account » (e-mail and password).
 * A new account is confirmed by a link in the mailbox; « Forgot password » sends another link.
 */
export function SignInFlow({
  as,
  pageName,
  mode,
}: {
  as?: "client" | "pro";
  pageName?: string;
  mode?: "signin" | "signup" | "forgot";
}) {
  useEffect(() => {
    if (!pageName) return;
    try {
      sessionStorage.setItem("sg.page-name", pageName);
    } catch {
      // Private browsing: the person will type the name again.
    }
  }, [pageName]);

  const t = useTranslations("auth");
  const locale = useLocale();
  const signedIn = useSignedIn(as);

  const [view, setView] = useState<View>(mode ?? (as ? "signup" : "signin"));
  const [firstName, setFirstName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [sentTo, setSentTo] = useState("");
  const [resendAt, setResendAt] = useState<number | null>(null);
  const [error, setError] = useState<string>();
  const [passwordError, setPasswordError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const secondsLeft = useCountdown(resendAt);

  const address = email.trim();
  const go = (next: View) => {
    setError(undefined);
    setPasswordError(undefined);
    setView(next);
  };

  const run = async (action: () => Promise<void>) => {
    setError(undefined);
    setPasswordError(undefined);
    setBusy(true);
    try {
      await action();
    } catch (err) {
      if (err instanceof ApiError) {
        const fields = (err.body.fields ?? {}) as Record<string, string[] | undefined>;
        if (fields.password?.length) setPasswordError(fields.password.join(" "));
        else setError(err.body.message || t("errors.network"));
        if (err.body.code === "email_not_confirmed") {
          setSentTo(address);
          setResendAt(Date.now() + RESEND_SECONDS * 1000);
          setView("checkMail");
        }
      } else {
        setError(t("errors.network"));
      }
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (view === "signin") {
      void run(async () => signedIn(await loginWithPassword({ identifier: address, password })));
    } else if (view === "signup") {
      void run(async () => {
        const result = await signUp({ email: address, password, first_name: firstName, locale });
        setSentTo(result.sent_to);
        setResendAt(Date.now() + RESEND_SECONDS * 1000);
        setView("checkMail");
      });
    } else if (view === "forgot") {
      void run(async () => {
        const result = await forgotPassword(address);
        setSentTo(result.sent_to);
        setView("resetSent");
      });
    }
  };

  const resend = () =>
    void run(async () => {
      await resendConfirmation(address);
      setResendAt(Date.now() + RESEND_SECONDS * 1000);
    });

  if (view === "checkMail" || view === "resetSent") {
    const title = view === "checkMail" ? t("mail.title") : t("reset.sentTitle");
    const text =
      view === "checkMail"
        ? t("mail.text", { email: sentTo || address })
        : t("reset.sentText", { email: sentTo || address });
    return (
      <section aria-labelledby="mail-title" className="flex flex-col gap-6">
        <span
          aria-hidden
          className="bg-poudre text-hibiscus grid size-20 place-items-center self-start rounded-full"
        >
          <EnvelopeSimple size={40} weight="duotone" />
        </span>
        <div className="flex items-start justify-between gap-3">
          <h1 id="mail-title" className="font-display text-headline font-black">
            {title}
          </h1>
          <SpeakButton text={`${title}. ${text}`} />
        </div>
        <p className="text-lead" role="status">
          {text}
        </p>
        <p className="text-prune-doux">{t("mail.spam")}</p>
        <ErrorMessage message={error} />
        {view === "checkMail" && (
          <Button variant="secondary" disabled={secondsLeft > 0 || busy} onClick={resend}>
            {secondsLeft > 0 ? t("mail.resendIn", { seconds: secondsLeft }) : t("mail.resend")}
          </Button>
        )}
        <Button
          variant="quiet"
          icon={<ArrowLeft size={20} weight="bold" />}
          className="self-start"
          onClick={() => go(view === "checkMail" ? "signup" : "signin")}
        >
          {view === "checkMail" ? t("mail.change") : t("reset.back")}
        </Button>
      </section>
    );
  }

  const titles: Record<"signin" | "signup" | "forgot", string> = {
    signin: t("signin.title"),
    signup: as === "pro" ? t("titlePro") : t("signup.title"),
    forgot: t("forgot.title"),
  };
  const title = titles[view];
  const subtitles: Record<"signin" | "signup" | "forgot", string> = {
    signin: t("signin.subtitle"),
    signup: t("signup.subtitle"),
    forgot: t("forgot.subtitle"),
  };
  const ready =
    !!address &&
    (view === "forgot" || password.length > 0) &&
    (view !== "signup" || firstName.trim().length > 0);

  return (
    <section aria-labelledby="auth-title" className="flex flex-col gap-6">
      {view !== "forgot" && (
        <div
          role="tablist"
          aria-label={t("tabs")}
          className="bg-poudre grid grid-cols-2 gap-1 rounded-full p-1"
        >
          <Tab selected={view === "signin"} onClick={() => go("signin")}>
            {t("signin.tab")}
          </Tab>
          <Tab selected={view === "signup"} onClick={() => go("signup")}>
            {t("signup.tab")}
          </Tab>
        </div>
      )}

      <div className="flex items-start justify-between gap-3">
        <h1 id="auth-title" className="font-display text-headline font-black">
          {title}
        </h1>
        <SpeakButton text={`${title}. ${subtitles[view]}`} />
      </div>
      <p className="text-prune-doux">{subtitles[view]}</p>

      <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
        {view === "signup" && (
          <Input
            label={t("signup.firstName")}
            autoComplete="given-name"
            value={firstName}
            maxLength={150}
            onChange={(event) => setFirstName(event.target.value)}
          />
        )}
        <Input
          label={t("emailLabel")}
          type="email"
          inputMode="email"
          autoComplete="email"
          autoCapitalize="none"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="awa@exemple.com"
        />
        {view !== "forgot" && (
          <PasswordField
            label={view === "signup" ? t("password.choose") : t("password.label")}
            autoComplete={view === "signup" ? "new-password" : "current-password"}
            hint={view === "signup" ? t("password.hint") : undefined}
            error={passwordError}
            value={password}
            onChange={setPassword}
          />
        )}

        <ErrorMessage message={error} />

        <Button
          type="submit"
          size="lg"
          fullWidth
          disabled={busy || !ready}
          icon={
            view === "signup" ? (
              <UserPlus size={22} weight="bold" />
            ) : view === "signin" ? (
              <SignInIcon size={22} weight="bold" />
            ) : (
              <EnvelopeSimple size={22} weight="bold" />
            )
          }
        >
          {view === "signup"
            ? t("signup.submit")
            : view === "signin"
              ? t("signin.submit")
              : t("forgot.submit")}
        </Button>
      </form>

      {view === "signin" && (
        <Button variant="quiet" className="self-start" onClick={() => go("forgot")}>
          {t("signin.forgot")}
        </Button>
      )}
      {view === "forgot" && (
        <Button
          variant="quiet"
          icon={<ArrowLeft size={20} weight="bold" />}
          className="self-start"
          onClick={() => go("signin")}
        >
          {t("reset.back")}
        </Button>
      )}
      <p className="text-small text-prune-doux">{t("privacy")}</p>
    </section>
  );
}

function Tab({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={selected}
      onClick={onClick}
      className={cn(
        "min-h-12 rounded-full px-4 font-bold transition-colors",
        selected ? "bg-carte text-prune border-trait border" : "text-prune-doux",
      )}
    >
      {children}
    </button>
  );
}
