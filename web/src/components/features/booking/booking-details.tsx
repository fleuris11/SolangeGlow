"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { BookableService } from "@/lib/api/booking";
import { durationLabel } from "@/lib/booking/time";
import { formatMoney } from "@/lib/money";

/** « Check and book »: the summary, the rules, her details, the group, the button. */
export function DetailsStep({
  service,
  optionNames,
  when,
  minutes,
  staffName,
  price,
  discount,
  deposit,
  freeCancelHours,
  autoConfirm,
  needsSignIn,
  onSignIn,
  guestFields,
  note,
  onNote,
  signedIn,
  size,
  onSize,
  icons,
  busy,
  onConfirm,
  proName,
  giftCode,
  onGiftCode,
  consent,
  onConsent,
}: {
  service: BookableService;
  optionNames: string[];
  when: string;
  minutes: number;
  staffName: string | null;
  price: number | null;
  discount: number;
  deposit: number;
  freeCancelHours: number;
  autoConfirm: boolean;
  needsSignIn: boolean;
  onSignIn: () => void;
  guestFields: ReactNode;
  note: string;
  onNote: (value: string) => void;
  signedIn: boolean;
  size: number;
  onSize: (value: number) => void;
  icons: { group: ReactNode; calendar: ReactNode };
  busy: boolean;
  onConfirm: () => void;
  proName: string;
  giftCode: string;
  onGiftCode: (value: string) => void;
  consent: boolean;
  onConsent: (value: boolean) => void;
}) {
  const t = useTranslations("booking.flow");
  const locale = useLocale();
  return (
    <div className="flex flex-col gap-5">
      <dl className="border-trait rounded-card flex flex-col gap-3 border p-4">
        <div>
          <dt className="text-small text-prune-doux">{t("service")}</dt>
          <dd className="font-bold">
            {service.name}
            {optionNames.length > 0 && ` + ${optionNames.join(", ")}`}
          </dd>
        </div>
        <div>
          <dt className="text-small text-prune-doux">{t("time")}</dt>
          <dd className="font-bold">
            {when} ({durationLabel(minutes, locale)})
          </dd>
        </div>
        {staffName && (
          <div>
            <dt className="text-small text-prune-doux">{t("with")}</dt>
            <dd className="font-bold">{staffName}</dd>
          </div>
        )}
        <div>
          <dt className="text-small text-prune-doux">{t("price")}</dt>
          <dd className="font-bold">
            {price === null ? t("quote") : formatMoney(price, service.currency, locale)}
            {discount > 0 && ` (-${discount} %)`}
          </dd>
        </div>
        {deposit > 0 && (
          <div>
            <dt className="text-small text-prune-doux">{t("depositLabel")}</dt>
            <dd className="font-bold">{formatMoney(deposit, service.currency, locale)}</dd>
            <dd className="text-small text-prune-doux">{t("depositHelp")}</dd>
          </div>
        )}
      </dl>
      <p className="text-small text-prune-doux">
        {deposit > 0 ? t("cancelRule", { hours: freeCancelHours }) : t("cancelFree")}
      </p>
      {!autoConfirm && <p className="text-small text-prune-doux">{t("manual")}</p>}

      {deposit > 0 && (
        <Input
          label={t("giftCode", { name: proName })}
          hint={t("giftCodeHint")}
          value={giftCode}
          autoCapitalize="characters"
          maxLength={20}
          onChange={(e) => onGiftCode(e.target.value.toUpperCase())}
        />
      )}
      {needsSignIn ? (
        <div className="bg-poudre rounded-card flex flex-col gap-3 p-4">
          <p className="font-bold">{deposit > 0 ? t("signInDeposit") : t("signInNeeded")}</p>
          <Button size="lg" fullWidth onClick={onSignIn}>
            {t("signIn")}
          </Button>
        </div>
      ) : (
        <>
          {guestFields}
          <Input
            label={t("note")}
            hint={t("noteHint")}
            value={note}
            maxLength={500}
            onChange={(e) => onNote(e.target.value)}
          />
          {signedIn && (
            <div className="border-trait rounded-card flex flex-col gap-2 border p-4">
              <p className="flex items-center gap-2 font-bold">
                {icons.group}
                {t("groupTitle")}
              </p>
              <div className="flex items-center gap-3">
                <Button
                  variant="secondary"
                  aria-label={t("less")}
                  disabled={size <= 1}
                  onClick={() => onSize(size - 1)}
                >
                  −
                </Button>
                <span className="min-w-24 text-center font-bold" aria-live="polite">
                  {t("people", { count: size })}
                </span>
                <Button
                  variant="secondary"
                  aria-label={t("more")}
                  disabled={size >= 8}
                  onClick={() => onSize(size + 1)}
                >
                  +
                </Button>
              </div>
              {size > 1 && <p className="text-small text-prune-doux">{t("groupHelp")}</p>}
            </div>
          )}
          <label className="flex min-h-12 items-start gap-3">
            <input
              type="checkbox"
              className="accent-hibiscus mt-1 size-6 shrink-0"
              checked={consent}
              onChange={(e) => onConsent(e.target.checked)}
            />
            <span>{t("consent", { name: proName })}</span>
          </label>
          <Button size="lg" fullWidth disabled={busy} onClick={onConfirm}>
            {icons.calendar}
            {size > 1
              ? t("bookGroup", { count: size })
              : deposit > 0 && !giftCode
                ? t("payDeposit", { amount: formatMoney(deposit, service.currency, locale) })
                : t("book", { when })}
          </Button>
        </>
      )}
    </div>
  );
}
