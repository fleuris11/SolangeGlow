"use client";

import {
  BellRinging,
  DeviceMobile,
  EnvelopeSimple,
  Key,
  SignOut,
  Trash,
  WhatsappLogo,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { ErrorMessage } from "@/components/features/auth/error-message";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import {
  deleteAccount,
  logout,
  logoutEverywhere,
  setPassword,
  updateMe,
  type Me,
} from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { useSetMe } from "@/lib/auth/use-me";
import { useRouter } from "@/lib/i18n/navigation";

/** Notifications, optional password, sessions and account deletion. */
export function AccountSettings({ me }: { me: Me }) {
  const t = useTranslations("account");
  const toast = useToast();
  const setMe = useSetMe();
  const router = useRouter();
  const [password, setPasswordValue] = useState("");
  const [passwordError, setPasswordError] = useState<string>();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const toggle = async (
    field: "notify_whatsapp" | "notify_email" | "notify_push",
    value: boolean,
  ) => {
    setMe(await updateMe({ [field]: value }));
    toast(t("saved"));
  };

  const savePassword = async (event: FormEvent) => {
    event.preventDefault();
    setPasswordError(undefined);
    try {
      await setPassword(password);
      setPasswordValue("");
      setMe({ ...me, has_password: true });
      toast(t("password.saved"));
    } catch (err) {
      setPasswordError(
        err instanceof ApiError ? (err.fieldMessage("password") ?? err.body.message) : t("error"),
      );
    }
  };

  const leave = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true);
    try {
      await action();
      setMe(null);
      toast(message);
      router.replace("/");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-10">
      <section aria-labelledby="notify-title" className="flex flex-col gap-3">
        <h2 id="notify-title" className="text-title font-bold">
          {t("notifications")}
        </h2>
        <SwitchRow
          icon={<WhatsappLogo size={28} weight="duotone" />}
          label={t("notifyWhatsapp")}
          description={t("notifyWhatsappText")}
          checked={me.notify_whatsapp}
          onChange={(value) => void toggle("notify_whatsapp", value)}
        />
        <SwitchRow
          icon={<EnvelopeSimple size={28} weight="duotone" />}
          label={t("notifyEmail")}
          description={t("notifyEmailText")}
          checked={me.notify_email}
          onChange={(value) => void toggle("notify_email", value)}
        />
        <SwitchRow
          icon={<BellRinging size={28} weight="duotone" />}
          label={t("notifyPush")}
          description={t("notifyPushText")}
          checked={me.notify_push}
          onChange={(value) => void toggle("notify_push", value)}
        />
      </section>

      <section aria-labelledby="password-title" className="flex flex-col gap-3">
        <h2 id="password-title" className="text-title font-bold">
          {t("password.title")}
        </h2>
        <p className="text-prune-doux">
          {me.has_password ? t("password.textSet") : t("password.textNone")}
        </p>
        <form onSubmit={savePassword} className="flex flex-col gap-3" noValidate>
          <Input
            label={me.has_password ? t("password.change") : t("password.create")}
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPasswordValue(event.target.value)}
            leading={<Key size={22} weight="duotone" />}
          />
          <ErrorMessage message={passwordError} />
          <Button type="submit" variant="secondary" disabled={!password} className="self-start">
            {t("password.save")}
          </Button>
        </form>
      </section>

      <section aria-labelledby="sessions-title" className="flex flex-col items-start gap-3">
        <h2 id="sessions-title" className="text-title font-bold">
          {t("sessions")}
        </h2>
        <Button
          variant="secondary"
          icon={<SignOut size={22} weight="bold" />}
          disabled={busy}
          onClick={() => void leave(logout, t("signedOut"))}
        >
          {t("signOut")}
        </Button>
        <Button
          variant="quiet"
          icon={<DeviceMobile size={22} weight="duotone" />}
          disabled={busy}
          onClick={() => void leave(logoutEverywhere, t("signedOutEverywhere"))}
        >
          {t("signOutEverywhere")}
        </Button>
      </section>

      <section aria-labelledby="delete-title" className="flex flex-col items-start gap-3">
        <h2 id="delete-title" className="text-title font-bold">
          {t("delete.title")}
        </h2>
        <p className="text-prune-doux">{t("delete.text")}</p>
        <Button
          variant="quiet"
          className="text-alerte"
          icon={<Trash size={22} weight="duotone" />}
          onClick={() => setConfirmDelete(true)}
        >
          {t("delete.cta")}
        </Button>
        <Sheet
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title={t("delete.confirmTitle")}
          description={t("delete.confirmText")}
        >
          <div className="flex flex-col gap-3">
            <Button
              size="lg"
              fullWidth
              disabled={busy}
              onClick={() => void leave(deleteAccount, t("delete.done"))}
            >
              {t("delete.confirm")}
            </Button>
            <Button variant="secondary" fullWidth onClick={() => setConfirmDelete(false)}>
              {t("delete.cancel")}
            </Button>
          </div>
        </Sheet>
      </section>
    </div>
  );
}
