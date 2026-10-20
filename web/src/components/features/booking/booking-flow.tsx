"use client";

import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useMemo, useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { ApiError, hasSession } from "@/lib/api/client";
import {
  book,
  createGroup,
  getSlots,
  joinWaitlist,
  type BookableService,
  type Booked,
  type BookingPage,
  type Group,
  type SlotDay,
} from "@/lib/api/booking";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { addDays, dayName, durationLabel, localDay, timeAt } from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { usePathname, useRouter } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

// Shown after the booking only: downloaded then (ADR-004).
const BookedScreen = dynamic(() => import("./booking-done").then((m) => m.BookedScreen));
const GroupCreated = dynamic(() => import("./booking-done").then((m) => m.GroupCreated));
// The last step comes after choosing a time: downloaded then.
const DetailsStep = dynamic(() => import("./booking-details").then((m) => m.DetailsStep));

export type BookingIcons = {
  clock: ReactNode;
  person: ReactNode;
  calendar: ReactNode;
  bell: ReactNode;
  group: ReactNode;
  lightning: ReactNode;
};

type Step = "service" | "staff" | "time" | "details";

const subscribeNothing = () => () => {};
const DAYS = 7;

function priceText(service: BookableService, locale: string, quote: string) {
  return service.price_minor === null
    ? quote
    : formatMoney(service.price_minor, service.currency, locale);
}

/** The whole booking: service, person, time, details. One choice per screen. */
export function BookingFlow({
  page,
  slug,
  initialServiceId,
  postId,
  icons,
}: {
  page: BookingPage;
  slug: string;
  initialServiceId?: string;
  postId?: string;
  icons: BookingIcons;
}) {
  const t = useTranslations("booking.flow");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const signedIn = useSyncExternalStore(subscribeNothing, hasSession, () => false);
  const zone = page.pro.timezone;
  const initial = page.services.find((s) => s.id === initialServiceId);

  const [service, setService] = useState<BookableService | undefined>(initial);
  const [optionIds, setOptionIds] = useState<string[]>([]);
  const [staffId, setStaffId] = useState<string | null>(null);
  const [firstDay, setFirstDay] = useState(page.first_day);
  const [chosenDay, setDay] = useState<string | null>(null);
  const [start, setStart] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [note, setNote] = useState("");
  const [size, setSize] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<Booked | null>(null);
  const [group, setGroup] = useState<Group | null>(null);
  const [waiting, setWaiting] = useState<"idle" | "form" | "done">("idle");

  const staffFor = useMemo(
    () =>
      service
        ? page.staff.filter((m) => m.service_ids.length === 0 || m.service_ids.includes(service.id))
        : [],
    [page.staff, service],
  );
  const steps: Step[] =
    staffFor.length > 1 ? ["service", "staff", "time", "details"] : ["service", "time", "details"];
  const [step, setStep] = useState<Step>(
    initial ? (staffFor.length > 1 ? "staff" : "time") : "service",
  );
  const index = steps.indexOf(step);

  const slotsQuery = useQuery({
    queryKey: ["slots", slug, service?.id, staffId, optionIds.join(","), firstDay],
    queryFn: () =>
      getSlots(slug, {
        service: service!.id,
        day: firstDay,
        days: DAYS,
        ...(staffId ? { staff: staffId } : {}),
        ...(optionIds.length ? { options: optionIds.join(",") } : {}),
      }),
    enabled: !!service && step === "time",
  });
  const days: SlotDay[] | null = slotsQuery.data?.days ?? (slotsQuery.isError ? [] : null);
  const nextDay = slotsQuery.data?.next_day ?? null;
  const firstFree = days?.find((d) => d.slots.length > 0)?.day;
  // The day she chose, else the first day with a free place.
  const day =
    chosenDay && (!days || days.some((d) => d.day === chosenDay))
      ? chosenDay
      : (firstFree ?? chosenDay ?? firstDay);

  const options = service?.options.filter((o) => optionIds.includes(o.id)) ?? [];
  const minutes =
    (service?.duration_minutes ?? 0) + options.reduce((sum, o) => sum + o.extra_minutes, 0);
  const slot = days?.flatMap((d) => d.slots).find((s) => s.start === start);
  const discount = slot?.discount_percent ?? 0;
  const basePrice =
    service && service.price_minor !== null
      ? service.price_minor + options.reduce((sum, o) => sum + o.price_minor, 0)
      : null;
  const price = basePrice === null ? null : Math.round((basePrice * (100 - discount)) / 100);
  const deposit = service?.deposit_minor ?? 0;
  const when = start
    ? t("when", { day: dayName(localDay(start, zone), locale), time: timeAt(start, zone, locale) })
    : "";
  const chosenStaff = page.staff.find((m) => m.id === (staffId ?? slot?.staff_id));

  const go = (next: Step) => {
    setError(null);
    setStep(next);
    window.scrollTo({ top: 0 });
  };
  const back = () => index > 0 && go(steps[index - 1] as Step);

  const signInFirst = () => {
    rememberReturnPath(`${pathname}${service ? `?service=${service.id}` : ""}`);
    router.push("/auth?as=client");
  };

  const fail = (caught: unknown) => {
    setError(caught instanceof ApiError ? caught.message : t("error"));
    if (caught instanceof ApiError && caught.code === "slot_taken") {
      setStart(null);
      go("time");
    }
  };

  const confirm = async () => {
    if (!service || !start) return;
    setBusy(true);
    setError(null);
    try {
      if (size > 1) {
        setGroup(await createGroup(slug, { service_id: service.id, start, size }));
        return;
      }
      const answer = await book(slug, {
        service_id: service.id,
        start,
        staff_id: staffId,
        option_ids: optionIds,
        note,
        ...(signedIn ? {} : { guest_name: name, guest_phone: phone }),
        ...(postId ? { post_id: postId } : {}),
      });
      if (answer.checkout_url) {
        window.location.assign(answer.checkout_url);
        return;
      }
      setDone(answer);
      window.scrollTo({ top: 0 });
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  };

  const wait = async () => {
    if (!service) return;
    setBusy(true);
    setError(null);
    try {
      await joinWaitlist(slug, {
        service_id: service.id,
        day,
        staff_id: staffId,
        ...(signedIn ? {} : { guest_name: name, guest_phone: phone }),
      });
      setWaiting("done");
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(false);
    }
  };

  if (done) return <BookedScreen booked={done} zone={zone} />;
  if (group) return <GroupCreated group={group} />;

  const title = {
    service: t("titleService"),
    staff: t("titleStaff"),
    time: t("titleTime"),
    details: t("titleDetails"),
  }[step];
  const current = days?.find((d) => d.day === day);
  const guestFields = !signedIn && (
    <div className="flex flex-col gap-4">
      <Input
        label={t("name")}
        value={name}
        onChange={(e) => setName(e.target.value)}
        autoComplete="given-name"
      />
      <Input
        label={t("phone")}
        hint={t("phoneHint")}
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        inputMode="tel"
        autoComplete="tel"
      />
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      <Stepper current={index + 1} total={steps.length} onBack={index > 0 ? back : undefined} />
      <div className="flex items-center gap-2">
        <h2 className="text-headline flex-1 font-bold">{title}</h2>
        <SpeakButton text={title} />
      </div>
      {error && (
        <p role="alert" className="bg-poudre text-alerte rounded-2xl p-3 font-bold">
          {error}
        </p>
      )}

      {step === "service" && (
        <ul className="flex flex-col gap-2">
          {page.services.map((item) => {
            const selected = service?.id === item.id;
            return (
              <li key={item.id} className="flex flex-col gap-2">
                <button
                  type="button"
                  aria-pressed={selected}
                  onClick={() => {
                    setService(item);
                    setOptionIds([]);
                    setStart(null);
                    if (item.options.length === 0) {
                      const people = page.staff.filter(
                        (m) => m.service_ids.length === 0 || m.service_ids.includes(item.id),
                      );
                      go(people.length > 1 ? "staff" : "time");
                    }
                  }}
                  className={cn(
                    "rounded-card flex min-h-16 w-full items-center gap-3 border-2 p-4 text-left",
                    selected
                      ? "border-hibiscus bg-poudre"
                      : "border-trait bg-carte hover:bg-poudre",
                  )}
                >
                  <span className="flex min-w-0 flex-1 flex-col gap-1">
                    <span className="font-bold">{item.name}</span>
                    <span className="text-small text-prune-doux flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="flex items-center gap-1">
                        {icons.clock}
                        {durationLabel(item.duration_minutes, locale)}
                      </span>
                      {item.deposit_minor > 0 && (
                        <span>
                          {t("deposit", {
                            amount: formatMoney(item.deposit_minor, item.currency, locale),
                          })}
                        </span>
                      )}
                    </span>
                  </span>
                  <span className="shrink-0 font-bold">{priceText(item, locale, t("quote"))}</span>
                </button>
                {selected && item.options.length > 0 && (
                  <fieldset className="border-trait rounded-card flex flex-col gap-2 border p-4">
                    <legend className="px-1 font-bold">{t("options")}</legend>
                    {item.options.map((option) => (
                      <label key={option.id} className="flex min-h-12 items-center gap-3">
                        <input
                          type="checkbox"
                          className="accent-hibiscus size-6"
                          checked={optionIds.includes(option.id)}
                          onChange={(e) =>
                            setOptionIds((ids) =>
                              e.target.checked
                                ? [...ids, option.id]
                                : ids.filter((id) => id !== option.id),
                            )
                          }
                        />
                        <span className="flex-1">{option.name}</span>
                        <span className="text-small text-prune-doux">
                          {option.price_minor > 0 &&
                            `+${formatMoney(option.price_minor, item.currency, locale)}`}
                          {option.extra_minutes > 0 &&
                            ` +${durationLabel(option.extra_minutes, locale)}`}
                        </span>
                      </label>
                    ))}
                    <Button
                      size="lg"
                      fullWidth
                      onClick={() => go(staffFor.length > 1 ? "staff" : "time")}
                    >
                      {t("next")}
                    </Button>
                  </fieldset>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {step === "staff" && (
        <ul className="flex flex-col gap-2">
          {[null, ...staffFor].map((member) => (
            <li key={member?.id ?? "any"}>
              <button
                type="button"
                aria-pressed={staffId === (member?.id ?? null)}
                onClick={() => {
                  setStaffId(member?.id ?? null);
                  setStart(null);
                  go("time");
                }}
                className={cn(
                  "rounded-card flex min-h-16 w-full items-center gap-3 border-2 p-4 text-left font-bold",
                  staffId === (member?.id ?? null)
                    ? "border-hibiscus bg-poudre"
                    : "border-trait bg-carte hover:bg-poudre",
                )}
              >
                <span
                  aria-hidden
                  className="bg-poudre text-hibiscus flex size-10 shrink-0 items-center justify-center rounded-full"
                  style={member ? { backgroundColor: member.color, color: "white" } : undefined}
                >
                  {member ? member.name.slice(0, 1) : icons.person}
                </span>
                {member ? member.name : t("anyone")}
              </button>
            </li>
          ))}
        </ul>
      )}

      {step === "time" && (
        <div className="flex flex-col gap-4">
          <div className="-mx-4 overflow-x-auto px-4" tabIndex={0} aria-label={t("days")}>
            <div role="tablist" aria-label={t("days")} className="flex gap-2">
              {Array.from({ length: DAYS }, (_, i) => addDays(firstDay, i)).map((d) => {
                const info = days?.find((x) => x.day === d);
                const full = info !== undefined && info.slots.length === 0;
                return (
                  <button
                    key={d}
                    type="button"
                    role="tab"
                    aria-selected={day === d}
                    onClick={() => {
                      setDay(d);
                      setWaiting("idle");
                    }}
                    className={cn(
                      "flex min-h-16 min-w-20 flex-col items-center justify-center rounded-2xl border-2 px-2",
                      day === d ? "border-hibiscus bg-hibiscus text-sur-hibiscus" : "border-trait",
                      full && day !== d && "text-prune-doux",
                    )}
                  >
                    <span className="text-small font-bold">{dayName(d, locale, true)}</span>
                    <span className="text-small">
                      {full ? t("full") : info ? t("free", { count: info.slots.length }) : "…"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
          <div className="flex justify-between gap-2">
            <Button
              variant="quiet"
              disabled={firstDay <= page.first_day}
              onClick={() => {
                setDay(null);
                setFirstDay(
                  addDays(firstDay, -DAYS) < page.first_day
                    ? page.first_day
                    : addDays(firstDay, -DAYS),
                );
              }}
            >
              {t("previousWeek")}
            </Button>
            <Button
              variant="quiet"
              disabled={!nextDay}
              onClick={() => {
                if (!nextDay) return;
                setDay(null);
                setFirstDay(nextDay);
              }}
            >
              {t("nextWeek")}
            </Button>
          </div>
          {days === null ? (
            <p className="text-prune-doux" role="status">
              {t("loading")}
            </p>
          ) : current && current.slots.length > 0 ? (
            <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4" aria-label={dayName(day, locale)}>
              {current.slots.map((item) => (
                <li key={item.start}>
                  <button
                    type="button"
                    aria-pressed={start === item.start}
                    onClick={() => {
                      setStart(item.start);
                      go("details");
                    }}
                    className={cn(
                      "flex min-h-12 w-full flex-col items-center justify-center rounded-full border-2 font-bold",
                      start === item.start
                        ? "border-hibiscus bg-hibiscus text-sur-hibiscus"
                        : "border-trait hover:bg-poudre",
                    )}
                  >
                    {timeAt(item.start, zone, locale)}
                    {item.discount_percent > 0 && (
                      <span className="text-small text-feuille flex items-center gap-1">
                        {icons.lightning}-{item.discount_percent} %
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="bg-poudre rounded-card flex flex-col gap-3 p-4">
              <p className="font-bold">{t("noSlot", { day: dayName(day, locale) })}</p>
              {waiting === "done" ? (
                <p role="status" className="text-feuille font-bold">
                  {t("waitingDone")}
                </p>
              ) : waiting === "form" ? (
                <>
                  {guestFields}
                  <Button size="lg" fullWidth disabled={busy} onClick={() => void wait()}>
                    {icons.bell}
                    {t("waitCta")}
                  </Button>
                </>
              ) : (
                <Button
                  variant="secondary"
                  fullWidth
                  onClick={() => (signedIn ? void wait() : setWaiting("form"))}
                >
                  {icons.bell}
                  {t("wait")}
                </Button>
              )}
              <p className="text-small text-prune-doux">{t("waitHelp")}</p>
            </div>
          )}
        </div>
      )}

      {step === "details" && service && start && (
        <DetailsStep
          service={service}
          optionNames={options.map((o) => o.name)}
          when={when}
          minutes={minutes}
          staffName={chosenStaff && staffFor.length > 1 ? chosenStaff.name : null}
          price={price}
          discount={discount}
          deposit={deposit}
          freeCancelHours={page.free_cancel_hours}
          autoConfirm={page.auto_confirm}
          needsSignIn={!signedIn && (deposit > 0 || !page.accepts_guests)}
          onSignIn={signInFirst}
          guestFields={guestFields}
          note={note}
          onNote={setNote}
          signedIn={signedIn}
          size={size}
          onSize={setSize}
          icons={icons}
          busy={busy || (!signedIn && (!name.trim() || phone.trim().length < 8))}
          onConfirm={() => void confirm()}
        />
      )}
    </div>
  );
}
