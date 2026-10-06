"use client";

import { Envelope, Phone } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState, type FormEvent } from "react";

import { ErrorMessage } from "@/components/features/auth/error-message";
import { PhoneField, toInternational } from "@/components/features/auth/phone-field";
import { Button } from "@/components/ui/button";
import { CodeInput } from "@/components/ui/code-input";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import {
  confirmContactChange,
  requestContactChange,
  type CodeRequest,
  type Me,
} from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { useSetMe } from "@/lib/auth/use-me";

const Sheet = dynamic(() => import("@/components/ui/sheet").then((m) => m.Sheet), { ssr: false });

type Kind = "phone" | "email";

/** Number and e-mail of the account; changing one needs a code sent to the new one. */
export function ContactChange({ me }: { me: Me }) {
  const t = useTranslations("contact");
  const [editing, setEditing] = useState<Kind | null>(null);

  const rows: { kind: Kind; value: string | null; icon: React.ReactNode }[] = [
    { kind: "phone", value: me.phone, icon: <Phone size={26} weight="duotone" /> },
    { kind: "email", value: me.email, icon: <Envelope size={26} weight="duotone" /> },
  ];

  return (
    <section aria-labelledby="contact-title" className="flex flex-col gap-3">
      <h2 id="contact-title" className="text-title font-bold">
        {t("title")}
      </h2>
      <ul className="flex flex-col gap-2">
        {rows.map(({ kind, value, icon }) => (
          <li
            key={kind}
            className="border-trait bg-carte rounded-card flex items-center gap-3 border p-4"
          >
            <span aria-hidden className="text-hibiscus shrink-0">
              {icon}
            </span>
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="font-bold">{t(kind)}</span>
              <span className="text-prune-doux truncate">{value ?? t("none")}</span>
            </span>
            <Button variant="secondary" onClick={() => setEditing(kind)}>
              {value ? t("change") : t("add")}
            </Button>
          </li>
        ))}
      </ul>
      {editing && <ChangeSheet kind={editing} onClose={() => setEditing(null)} />}
    </section>
  );
}

function ChangeSheet({ kind, onClose }: { kind: Kind; onClose: () => void }) {
  const t = useTranslations("contact");
  const locale = useLocale();
  const toast = useToast();
  const setMe = useSetMe();
  const [country, setCountry] = useState("BJ");
  const [value, setValue] = useState("");
  const [challenge, setChallenge] = useState<CodeRequest | null>(null);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [codeKey, setCodeKey] = useState(0);

  const message = (err: unknown) =>
    err instanceof ApiError && err.body.message ? err.body.message : t("error");

  const send = async (event: FormEvent) => {
    event.preventDefault();
    setError(undefined);
    setBusy(true);
    try {
      const destination = kind === "phone" ? toInternational(country, value) : value.trim();
      setChallenge(
        await requestContactChange(
          kind === "phone" ? { phone: destination, locale } : { email: destination, locale },
        ),
      );
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (code: string) => {
    if (!challenge) return;
    setError(undefined);
    setBusy(true);
    try {
      setMe(await confirmContactChange({ challenge_id: challenge.challenge_id, code }));
      toast(t(kind === "phone" ? "phoneSaved" : "emailSaved"));
      onClose();
    } catch (err) {
      setError(message(err));
      setCodeKey((k) => k + 1);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet
      open
      onOpenChange={(open) => !open && onClose()}
      title={t(kind === "phone" ? "sheetPhone" : "sheetEmail")}
      description={challenge ? t("codeSent") : t("sheetText")}
    >
      {challenge ? (
        <div className="flex flex-col gap-4">
          <CodeInput
            key={codeKey}
            label={t("codeLabel")}
            onComplete={confirm}
            disabled={busy}
            autoFocus
          />
          <ErrorMessage message={error} />
        </div>
      ) : (
        <form onSubmit={send} className="flex flex-col gap-4" noValidate>
          {kind === "phone" ? (
            <PhoneField
              country={country}
              onCountryChange={setCountry}
              value={value}
              onChange={setValue}
              autoFocus
            />
          ) : (
            <Input
              label={t("newEmail")}
              type="email"
              inputMode="email"
              autoComplete="email"
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          )}
          <ErrorMessage message={error} />
          <Button type="submit" size="lg" fullWidth disabled={busy || !value}>
            {t("sendCode")}
          </Button>
        </form>
      )}
    </Sheet>
  );
}
