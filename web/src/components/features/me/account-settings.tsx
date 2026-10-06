"use client";

import { BellRinging, CaretRight, DeviceMobile, Key, SignOut, Trash } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { ErrorMessage } from "@/components/features/auth/error-message";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { useToast } from "@/components/ui/toast";
import { deleteAccount, logout, logoutEverywhere, setPassword, type Me } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { useSetMe } from "@/lib/auth/use-me";
import { Link, useRouter } from "@/lib/i18n/navigation";

/** Link to notifications, optional password, sessions and account deletion. */
export function AccountSettings({ me }: { me: Me }) {
  const t = useTranslations("account");
  const toast = useToast();
  const setMe = useSetMe();
  const router = useRouter();
  const locale = useLocale();
  const [password, setPasswordValue] = useState("");
  const [passwordError, setPasswordError] = useState<string>();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

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
      <Link
        href="/notifications"
        className="border-trait bg-carte rounded-card flex items-center gap-4 border p-4"
      >
        <BellRinging aria-hidden size={28} weight="duotone" className="text-hibiscus shrink-0" />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="font-bold">{t("notifications")}</span>
          <span className="text-small text-prune-doux">{t("notificationsText")}</span>
        </span>
        <CaretRight aria-hidden size={20} weight="bold" />
      </Link>

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
              onClick={async () => {
                const { erase_after: eraseAfter } = await deleteAccount();
                const date = new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                  new Date(eraseAfter),
                );
                await leave(async () => undefined, t("delete.done", { date }));
              }}
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
