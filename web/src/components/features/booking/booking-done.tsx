"use client";

import { useLocale, useTranslations } from "next-intl";

import { Bloom } from "@/components/ui/bloom";
import { buttonClasses } from "@/components/ui/button";
import type { Booked, Group } from "@/lib/api/booking";
import { dayName, localDay, timeAt } from "@/lib/booking/time";
import { Link } from "@/lib/i18n/navigation";

/** Booked: confirmed (petals), or sent to the pro; a guest gets her link. */
export function BookedScreen({ booked, zone }: { booked: Booked; zone: string }) {
  const t = useTranslations("booking.flow");
  const locale = useLocale();
  const a = booked.appointment;
  const confirmed = a.status === "confirmed";
  const title = confirmed ? t("doneConfirmed") : t("doneRequested");
  const when = t("when", {
    day: dayName(localDay(a.starts_at, zone), locale),
    time: timeAt(a.starts_at, zone, locale),
  });
  return (
    <section aria-labelledby="booked" className="flex flex-col items-center gap-5 text-center">
      {confirmed && <Bloom label={t("doneConfirmed")} />}
      <h2 id="booked" className="font-display text-display font-black">
        {title}
      </h2>
      <p className="text-lead">
        {a.service_name}, {when}
      </p>
      <p className="text-prune-doux">
        {confirmed
          ? t("doneConfirmedHelp", { name: a.pro.name })
          : t("doneRequestedHelp", { name: a.pro.name })}
      </p>
      <p className="text-small text-prune-doux">{t("reference", { reference: a.reference })}</p>
      {booked.manage_url ? (
        <>
          <p className="text-small text-prune-doux">{t("guestLink")}</p>
          <Link href={booked.manage_url} className={buttonClasses({ size: "lg", fullWidth: true })}>
            {t("manage")}
          </Link>
        </>
      ) : (
        <Link
          href={`/appointments/${a.id}`}
          className={buttonClasses({ size: "lg", fullWidth: true })}
        >
          {t("seeAppointment")}
        </Link>
      )}
    </section>
  );
}

/** A group: the organiser shares the link, each person pays her share. */
export function GroupCreated({ group }: { group: Group }) {
  const t = useTranslations("booking.group");
  return (
    <section aria-labelledby="group" className="flex flex-col items-center gap-5 text-center">
      <h2 id="group" className="font-display text-display font-black">
        {t("created")}
      </h2>
      <p className="text-prune-doux">
        {group.share_minor > 0
          ? t("createdPayHelp")
          : t("createdHelp", { count: group.places.length })}
      </p>
      <Link href={group.share_url} className={buttonClasses({ size: "lg", fullWidth: true })}>
        {t("open")}
      </Link>
    </section>
  );
}
