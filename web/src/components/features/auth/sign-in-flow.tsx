"use client";

import { ArrowLeft, Envelope, Key, Phone, WhatsappLogo } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { CodeInput } from "@/components/ui/code-input";
import { Input } from "@/components/ui/input";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import {
  loginWithPassword,
  requestCode,
  updateMe,
  verifyCode,
  type CodeRequest,
  type SignIn,
} from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { useSetMe } from "@/lib/auth/use-me";
import { useRouter } from "@/lib/i18n/navigation";
import { usePreferences } from "@/lib/preferences/preferences-provider";
import { toProfile } from "@/lib/preferences/profile-sync";

import { ErrorMessage } from "./error-message";
import { PhoneField, toInternational } from "./phone-field";
import { useCountdown } from "./use-countdown";

type Method = "phone" | "email";
type Step = "identifier" | "code" | "password";

/** Sign-up and sign-in are one flow: number or e-mail, then the 6-digit code. */
export function SignInFlow({ as }: { as?: "client" | "pro" }) {
  const t = useTranslations("auth");
  const locale = useLocale();
  const router = useRouter();
  const toast = useToast();
  const setMe = useSetMe();
  const prefs = usePreferences();

  const [step, setStep] = useState<Step>("identifier");
  const [method, setMethod] = useState<Method>("phone");
  const [country, setCountry] = useState("BJ");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [challenge, setChallenge] = useState<(CodeRequest & { destination: string }) | null>(null);
  const [resendAt, setResendAt] = useState<number | null>(null);
  const [codeKey, setCodeKey] = useState(0);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const secondsLeft = useCountdown(resendAt);

  const destination = method === "phone" ? toInternational(country, phone) : email.trim();
  const messageOf = (err: unknown) =>
    err instanceof ApiError && err.body.message ? err.body.message : t("errors.network");

  const sendCode = async () => {
    setError(undefined);
    setBusy(true);
    try {
      const result = await requestCode(
        method === "phone" ? { phone: destination, locale } : { email: destination, locale },
      );
      setChallenge({ ...result, destination });
      setResendAt(Date.now() + result.resend_after * 1000);
      setCodeKey((key) => key + 1);
      setStep("code");
    } catch (err) {
      setError(messageOf(err));
      if (err instanceof ApiError && err.body.retry_after) {
        setResendAt(Date.now() + err.body.retry_after * 1000);
      }
    } finally {
      setBusy(false);
    }
  };

  const signedIn = async ({ created, user, deletion_cancelled: deletionCancelled }: SignIn) => {
    let me = user;
    if (created) {
      // Nothing is lost: choices made as a visitor become the profile's.
      me = await updateMe(toProfile(prefs)).catch(() => user);
    }
    setMe(me);
    if (me.onboarding_required) {
      router.replace(as ? { pathname: "/welcome", query: { as } } : "/welcome");
    } else {
      toast(deletionCancelled ? t("deletionCancelled") : t("welcomeBack"));
      router.replace("/");
    }
  };

  const onCode = async (code: string) => {
    if (!challenge) return;
    setError(undefined);
    setBusy(true);
    try {
      await signedIn(await verifyCode({ challenge_id: challenge.challenge_id, code, locale }));
    } catch (err) {
      setError(messageOf(err));
      // Empty boxes and the cursor back in the first one: the person types the code again.
      setCodeKey((key) => key + 1);
    } finally {
      setBusy(false);
    }
  };

  const onPassword = async (event: FormEvent) => {
    event.preventDefault();
    setError(undefined);
    setBusy(true);
    try {
      await signedIn(await loginWithPassword({ identifier: destination, password }));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  };

  const back = () => {
    setError(undefined);
    setStep("identifier");
  };

  if (step === "code" && challenge) {
    const sentText =
      challenge.channel === "console"
        ? t("code.sentToConsole")
        : t("code.sentTo", {
            channel: t(`channels.${challenge.channel}`),
            destination: challenge.destination,
          });
    return (
      <section aria-labelledby="code-title" className="flex flex-col gap-6">
        <Stepper current={2} total={2} onBack={back} />
        <div className="flex items-start justify-between gap-3">
          <h1 id="code-title" className="font-display text-headline font-black">
            {t("code.title")}
          </h1>
          <SpeakButton text={`${t("code.title")}. ${sentText}`} />
        </div>
        <p className="flex items-start gap-2">
          {challenge.channel === "whatsapp" ? (
            <WhatsappLogo
              aria-hidden
              size={24}
              weight="duotone"
              className="text-feuille shrink-0"
            />
          ) : (
            <Envelope aria-hidden size={24} weight="duotone" className="text-hibiscus shrink-0" />
          )}
          <span>{sentText}</span>
        </p>
        <CodeInput
          key={codeKey}
          label={t("code.label")}
          onComplete={onCode}
          disabled={busy}
          autoFocus
        />
        <ErrorMessage message={error} />
        <div className="flex flex-col items-start gap-2">
          <Button variant="secondary" disabled={secondsLeft > 0 || busy} onClick={sendCode}>
            {secondsLeft > 0 ? t("code.resendIn", { seconds: secondsLeft }) : t("code.resend")}
          </Button>
          <Button variant="quiet" icon={<ArrowLeft size={20} weight="bold" />} onClick={back}>
            {method === "phone" ? t("code.changePhone") : t("code.changeEmail")}
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="auth-title" className="flex flex-col gap-6">
      <Stepper current={1} total={2} />
      <div className="flex items-start justify-between gap-3">
        <h1 id="auth-title" className="font-display text-headline font-black">
          {as === "pro" ? t("titlePro") : t("title")}
        </h1>
        <SpeakButton text={`${t("title")}. ${t("subtitle")}`} />
      </div>
      <p className="text-prune-doux">{t("subtitle")}</p>

      <div role="group" aria-label={t("method")} className="flex flex-wrap gap-2">
        <Chip
          selected={method === "phone"}
          icon={<Phone size={22} weight="duotone" />}
          onClick={() => setMethod("phone")}
        >
          {t("byPhone")}
        </Chip>
        <Chip
          selected={method === "email"}
          icon={<Envelope size={22} weight="duotone" />}
          onClick={() => setMethod("email")}
        >
          {t("byEmail")}
        </Chip>
      </div>

      <form
        onSubmit={
          step === "password"
            ? onPassword
            : (event) => {
                event.preventDefault();
                void sendCode();
              }
        }
        className="flex flex-col gap-5"
        noValidate
      >
        {method === "phone" ? (
          <PhoneField
            country={country}
            onCountryChange={setCountry}
            value={phone}
            onChange={setPhone}
            autoFocus
          />
        ) : (
          <Input
            label={t("emailLabel")}
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="awa@exemple.com"
          />
        )}

        {step === "password" && (
          <Input
            label={t("password.label")}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        )}

        <ErrorMessage message={error} />

        <Button
          type="submit"
          size="lg"
          fullWidth
          disabled={busy || !destination || (step === "password" && !password)}
        >
          {step === "password" ? t("password.submit") : t("sendCode")}
        </Button>
      </form>

      <Button
        variant="quiet"
        icon={<Key size={20} weight="duotone" />}
        className="self-start"
        onClick={() => {
          setError(undefined);
          setStep(step === "password" ? "identifier" : "password");
        }}
      >
        {step === "password" ? t("password.useCode") : t("password.use")}
      </Button>
      <p className="text-small text-prune-doux">{t("privacy")}</p>
    </section>
  );
}
