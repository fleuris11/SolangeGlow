"use client";

import { Cake, Stack } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  getClientFile,
  getPackages,
  getPaymentMethods,
  recordInstallment,
  sellPackage,
  updateClientFile,
  spendSession,
  type OnSiteMethod,
} from "@/lib/api/glowpro";
import { formatMoney } from "@/lib/money";

import { PremiumOffer } from "./premium-gate";

/** The complete file of a client: contact, birthday, her yes to offers, her packages. */
export function ClientExtras({ recordId }: { recordId: string }) {
  const t = useTranslations("glowpro.clientFile");
  const tMethod = useTranslations("glowpro.methods");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = ["client-file", recordId];
  const query = useQuery({ queryKey: key, queryFn: () => getClientFile(recordId) });
  const methods = useQuery({ queryKey: ["salon-methods"], queryFn: getPaymentMethods });
  const packages = useQuery({
    queryKey: ["packages"],
    queryFn: getPackages,
    enabled: !!query.data?.premium,
  });
  const [email, setEmail] = useState<string | null>(null);
  const [day, setDay] = useState<string | null>(null);
  const [month, setMonth] = useState<string | null>(null);
  const [packageId, setPackageId] = useState("");
  const [times, setTimes] = useState("1");
  const [method, setMethod] = useState<OnSiteMethod | "">("");
  const [busy, setBusy] = useState(false);
  const file = query.data;

  const run = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: key });
      toast(done, "success");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  if (!file) return null;
  const consent = (channel: "email" | "whatsapp") =>
    file.consents.find((c) => c.channel === channel)?.granted ?? false;
  const monthName = (m: number) =>
    new Intl.DateTimeFormat(locale, { month: "long", timeZone: "UTC" }).format(
      new Date(Date.UTC(2000, m - 1, 1)),
    );
  const available = methods.data?.methods ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Input
        label={t("email")}
        type="email"
        value={email ?? file.email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <fieldset className="flex flex-col gap-2">
        <legend className="flex items-center gap-2 font-bold">
          <Cake aria-hidden size={22} className="text-hibiscus" />
          {t("birthday")}
        </legend>
        <div className="grid grid-cols-2 gap-3">
          <select
            aria-label={t("day")}
            value={day ?? String(file.birthday_day ?? "")}
            onChange={(e) => setDay(e.target.value)}
            className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
          >
            <option value="">{t("day")}</option>
            {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <select
            aria-label={t("month")}
            value={month ?? String(file.birthday_month ?? "")}
            onChange={(e) => setMonth(e.target.value)}
            className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
          >
            <option value="">{t("month")}</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>
                {monthName(m)}
              </option>
            ))}
          </select>
        </div>
      </fieldset>
      <Button
        variant="secondary"
        fullWidth
        disabled={busy}
        onClick={() =>
          void run(
            () =>
              updateClientFile(recordId, {
                ...(email !== null ? { email } : {}),
                ...(day !== null || month !== null
                  ? {
                      birthday_day: Number(day ?? file.birthday_day) || null,
                      birthday_month: Number(month ?? file.birthday_month) || null,
                    }
                  : {}),
              }),
            t("saved"),
          )
        }
      >
        {t("save")}
      </Button>

      <section aria-labelledby="consents" className="flex flex-col gap-2">
        <h3 id="consents" className="font-bold">
          {t("consents")}
        </h3>
        <p className="text-small text-prune-doux">{t("consentsHelp")}</p>
        {(["email", "whatsapp"] as const).map((channel) => (
          <SwitchRow
            key={channel}
            icon={null}
            label={t(`channel.${channel}`)}
            description={t("consentSource")}
            checked={consent(channel)}
            disabled={busy}
            onChange={(value) =>
              void run(
                () => updateClientFile(recordId, { [`${channel}_consent`]: value }),
                t("saved"),
              )
            }
          />
        ))}
      </section>

      <section aria-labelledby="client-packages" className="flex flex-col gap-3">
        <h3 id="client-packages" className="flex items-center gap-2 font-bold">
          <Stack aria-hidden size={22} className="text-hibiscus" />
          {t("packages")}
        </h3>
        {!file.premium ? (
          <PremiumOffer title={t("premiumTitle")} />
        ) : (
          <>
            {file.packages.map((sold) => (
              <div
                key={sold.id}
                className="border-trait flex flex-col gap-2 rounded-2xl border p-3"
              >
                <p className="font-bold">{sold.name}</p>
                <p className="text-small">
                  {t("sessions", { used: sold.sessions_used, total: sold.sessions_total })}
                </p>
                {sold.status === "active" && (
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void run(() => spendSession(sold.id), t("sessionUsed"))}
                  >
                    {t("useSession")}
                  </Button>
                )}
                {sold.installments
                  .filter((i) => i.status === "due")
                  .map((i) => (
                    <div key={i.id} className="flex items-center justify-between gap-2">
                      <span className="text-small">
                        {t("installment", {
                          amount: formatMoney(i.amount_minor, sold.currency, locale),
                          date: new Intl.DateTimeFormat(locale, {
                            day: "numeric",
                            month: "long",
                          }).format(new Date(`${i.due_on}T12:00:00Z`)),
                        })}
                      </span>
                      {available[0] && (
                        <Button
                          variant="quiet"
                          disabled={busy}
                          onClick={() =>
                            void run(
                              () => recordInstallment(i.id, available[0]!),
                              t("installmentPaid"),
                            )
                          }
                        >
                          {t("paidWith", { method: tMethod(available[0]) })}
                        </Button>
                      )}
                    </div>
                  ))}
              </div>
            ))}
            {(packages.data ?? []).length > 0 && available.length > 0 && (
              <div className="bg-poudre flex flex-col gap-3 rounded-2xl p-3">
                <label className="flex flex-col gap-2 font-bold">
                  {t("sell")}
                  <select
                    value={packageId}
                    onChange={(e) => setPackageId(e.target.value)}
                    className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
                  >
                    <option value="">{t("choosePackage")}</option>
                    {(packages.data ?? []).map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({formatMoney(p.price_minor, p.currency, locale)})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-2 font-bold">
                  {t("times")}
                  <select
                    value={times}
                    onChange={(e) => setTimes(e.target.value)}
                    className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
                  >
                    {[1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>
                        {t("timesValue", { count: n })}
                      </option>
                    ))}
                  </select>
                </label>
                <div
                  className="flex flex-wrap gap-2"
                  role="radiogroup"
                  aria-label={t("firstPayment")}
                >
                  {available.map((value) => (
                    <label key={value} className="flex min-h-12 items-center gap-2">
                      <input
                        type="radio"
                        name="sell-method"
                        className="accent-hibiscus size-6"
                        checked={method === value}
                        onChange={() => setMethod(value)}
                      />
                      {tMethod(value)}
                    </label>
                  ))}
                </div>
                <Button
                  fullWidth
                  disabled={busy || !packageId || !method}
                  onClick={() =>
                    void run(
                      () =>
                        sellPackage(recordId, {
                          package_id: packageId,
                          installments: Number(times),
                          method: method as OnSiteMethod,
                        }),
                      t("sold"),
                    )
                  }
                >
                  {t("sellCta")}
                </Button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
