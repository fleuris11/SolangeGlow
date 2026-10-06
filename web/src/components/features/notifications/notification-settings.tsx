"use client";

import {
  BellRinging,
  EnvelopeSimple,
  MoonStars,
  PaperPlaneTilt,
  WhatsappLogo,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";

import { ErrorMessage } from "@/components/features/auth/error-message";
import { Button } from "@/components/ui/button";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { updateMe, type Me } from "@/lib/api/accounts";
import { sendTestNotification } from "@/lib/api/notifications";
import { useSetMe } from "@/lib/auth/use-me";
import { disablePush, enablePush, pushState, type PushState } from "@/lib/notifications/push";

const timeClass =
  "rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 text-lead font-bold outline-none";

/** Channels the person accepts, and the night hours without phone alerts. */
export function NotificationSettings({ me }: { me: Me }) {
  const t = useTranslations("notifications.settings");
  const toast = useToast();
  const setMe = useSetMe();
  const [push, setPush] = useState<PushState | "loading">("loading");
  const [quietStart, setQuietStart] = useState(me.quiet_hours_start ?? "22:00");
  const [quietEnd, setQuietEnd] = useState(me.quiet_hours_end ?? "07:00");
  const [error, setError] = useState<string>();

  useEffect(() => {
    void pushState().then(setPush);
  }, []);

  const save = async (patch: Parameters<typeof updateMe>[0]) => {
    setMe(await updateMe(patch));
    toast(t("saved"));
  };

  const togglePush = async (on: boolean) => {
    setError(undefined);
    setPush("loading");
    try {
      const state = on ? await enablePush() : await disablePush();
      setPush(state);
      if (state === "denied") setError(t("pushDenied"));
      if (on && state === "on") await save({ notify_push: true });
    } catch {
      setPush(await pushState());
      setError(t("pushError"));
    }
  };

  const saveQuiet = async (event: FormEvent) => {
    event.preventDefault();
    await save({ quiet_hours_start: quietStart, quiet_hours_end: quietEnd });
  };

  const pushDescription =
    push === "unsupported"
      ? t("pushUnsupported")
      : push === "denied"
        ? t("pushDenied")
        : t("pushText");

  return (
    <section aria-labelledby="settings-title" className="flex flex-col gap-6">
      <h2 id="settings-title" className="text-title font-bold">
        {t("title")}
      </h2>

      <div className="flex flex-col gap-3">
        <SwitchRow
          icon={<BellRinging size={28} weight="duotone" />}
          label={t("push")}
          description={pushDescription}
          checked={push === "on"}
          disabled={push === "loading" || push === "unsupported" || push === "denied"}
          onChange={(value) => void togglePush(value)}
        />
        <SwitchRow
          icon={<EnvelopeSimple size={28} weight="duotone" />}
          label={t("email")}
          description={me.email ? t("emailText", { email: me.email }) : t("emailMissing")}
          checked={me.notify_email && !!me.email}
          disabled={!me.email}
          onChange={(value) => void save({ notify_email: value })}
        />
        <SwitchRow
          icon={<WhatsappLogo size={28} weight="duotone" />}
          label={t("whatsapp")}
          description={t("whatsappText")}
          checked={me.notify_whatsapp}
          disabled={!me.phone}
          onChange={(value) => void save({ notify_whatsapp: value })}
        />
      </div>

      <ErrorMessage message={error} />

      <form
        onSubmit={saveQuiet}
        aria-labelledby="quiet-title"
        className="border-trait bg-carte rounded-card flex flex-col gap-4 border p-4"
      >
        <h3 id="quiet-title" className="flex items-center gap-2 font-bold">
          <MoonStars aria-hidden size={26} weight="duotone" className="text-hibiscus" />
          {t("quietTitle")}
        </h3>
        <p className="text-small text-prune-doux">{t("quietText")}</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-2 font-bold">
            {t("quietFrom")}
            <input
              type="time"
              value={quietStart}
              onChange={(event) => setQuietStart(event.target.value)}
              className={timeClass}
            />
          </label>
          <label className="flex flex-col gap-2 font-bold">
            {t("quietTo")}
            <input
              type="time"
              value={quietEnd}
              onChange={(event) => setQuietEnd(event.target.value)}
              className={timeClass}
            />
          </label>
        </div>
        <Button type="submit" variant="secondary" className="self-start">
          {t("quietSave")}
        </Button>
      </form>

      <Button
        variant="quiet"
        className="self-start"
        icon={<PaperPlaneTilt size={22} weight="duotone" />}
        onClick={async () => {
          await sendTestNotification();
          toast(t("testSent"));
        }}
      >
        {t("test")}
      </Button>
    </section>
  );
}
