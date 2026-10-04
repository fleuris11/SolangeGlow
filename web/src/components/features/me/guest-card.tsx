"use client";

import { CalendarCheck, CheckCircle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { ErrorMessage } from "@/components/features/auth/error-message";
import { PhoneField, toInternational } from "@/components/features/auth/phone-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createGuest, getGuest } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";

/** Booking without an account: a first name and a number are enough. */
export function GuestCard() {
  const t = useTranslations("guest");
  const queryClient = useQueryClient();
  const guest = useQuery({ queryKey: ["guest"], queryFn: getGuest });
  const [firstName, setFirstName] = useState("");
  const [country, setCountry] = useState("BJ");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(undefined);
    setBusy(true);
    try {
      const created = await createGuest({
        first_name: firstName,
        phone: toInternational(country, phone),
      });
      queryClient.setQueryData(["guest"], created);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? (err.fieldMessage("phone") ?? err.fieldMessage("first_name") ?? err.body.message)
          : t("error"),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      aria-labelledby="guest-booking-title"
      className="border-trait bg-carte rounded-card flex flex-col gap-4 border p-5"
    >
      <CalendarCheck aria-hidden size={36} weight="duotone" className="text-hibiscus" />
      <h2 id="guest-booking-title" className="text-title font-bold">
        {t("title")}
      </h2>
      {guest.data ? (
        <p className="flex items-start gap-2">
          <CheckCircle aria-hidden size={24} weight="fill" className="text-feuille shrink-0" />
          <span>{t("saved", { name: guest.data.first_name, phone: guest.data.phone })}</span>
        </p>
      ) : (
        <>
          <p className="text-prune-doux">{t("text")}</p>
          <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
            <Input
              label={t("firstName")}
              autoComplete="given-name"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
              maxLength={150}
            />
            <PhoneField
              country={country}
              onCountryChange={setCountry}
              value={phone}
              onChange={setPhone}
            />
            <ErrorMessage message={error} />
            <Button type="submit" variant="secondary" disabled={busy || !firstName || !phone}>
              {t("cta")}
            </Button>
          </form>
        </>
      )}
    </section>
  );
}
