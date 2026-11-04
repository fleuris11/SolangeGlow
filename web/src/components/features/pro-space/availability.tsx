"use client";

import {
  ArrowRight,
  CalendarX,
  Clock,
  MapPin,
  PauseCircle,
  Plus,
  Timer,
  Trash,
  Van,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import {
  addPlace,
  closeManualSlot,
  getAgenda,
  getAgendaSettings,
  getManualSlots,
  getPlaces,
  openManualSlots,
  removePlace,
  setPlaceHours,
  updateAgendaSettings,
  type Place,
} from "@/lib/api/booking";
import { ApiError } from "@/lib/api/client";
import { dayName, localDay, timeAt, zonedToIso } from "@/lib/booking/time";
import { Link } from "@/lib/i18n/navigation";
import { weekdayName } from "@/lib/pros/format";

function Part({
  id,
  icon,
  title,
  help,
  children,
}: {
  id: string;
  icon: ReactNode;
  title: string;
  help?: string;
  children: ReactNode;
}) {
  return (
    <section
      aria-labelledby={id}
      className="border-trait rounded-card flex flex-col gap-4 border p-4"
    >
      <div>
        <h2 id={id} className="text-title flex items-center gap-2 font-bold">
          <span aria-hidden className="text-hibiscus inline-flex">
            {icon}
          </span>
          {title}
        </h2>
        {help && <p className="text-prune-doux mt-1">{help}</p>}
      </div>
      {children}
    </section>
  );
}

const minutes = (value: string) => {
  const [hours = 0, mins = 0] = value.split(":").map(Number);
  return hours * 60 + mins;
};

function useRun() {
  const t = useTranslations("proSpace.slots");
  const toast = useToast();
  const queryClient = useQueryClient();
  return async (action: () => Promise<unknown>, success: string) => {
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: ["availability"] });
      await queryClient.invalidateQueries({ queryKey: ["agenda-settings"] });
      toast(success, "success");
      return true;
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
      return false;
    }
  };
}

function OpenSlotForm({
  zone,
  places,
  staff,
}: {
  zone: string;
  places: Place[];
  staff: { id: string; name: string }[];
}) {
  const t = useTranslations("proSpace.slots");
  const run = useRun();
  const [day, setDay] = useState("");
  const [from, setFrom] = useState("09:00");
  const [to, setTo] = useState("12:00");
  const [place, setPlace] = useState("");
  const [person, setPerson] = useState("");
  const [repeat, setRepeat] = useState(0);
  const [busy, setBusy] = useState(false);
  const valid = !!day && minutes(to) > minutes(from);
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        setBusy(true);
        void run(
          () =>
            openManualSlots({
              starts_at: zonedToIso(day, minutes(from), zone),
              ends_at: zonedToIso(day, minutes(to), zone),
              place_id: place || null,
              staff_id: person || null,
              repeat_weeks: repeat,
            }),
          t("opened"),
        ).finally(() => setBusy(false));
      }}
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Input label={t("day")} type="date" value={day} onChange={(e) => setDay(e.target.value)} />
        <Input
          label={t("from")}
          type="time"
          step={300}
          value={from}
          onChange={(e) => setFrom(e.target.value)}
        />
        <Input
          label={t("to")}
          type="time"
          step={300}
          value={to}
          onChange={(e) => setTo(e.target.value)}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {places.length > 0 && (
          <label className="flex flex-col gap-2 font-bold">
            {t("place")}
            <select
              value={place}
              onChange={(e) => setPlace(e.target.value)}
              className="border-trait bg-carte rounded-field min-h-12 border-2 px-3"
            >
              <option value="">{t("mainPlace")}</option>
              {places.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {staff.length > 1 && (
          <label className="flex flex-col gap-2 font-bold">
            {t("person")}
            <select
              value={person}
              onChange={(e) => setPerson(e.target.value)}
              className="border-trait bg-carte rounded-field min-h-12 border-2 px-3"
            >
              <option value="">{t("everyone")}</option>
              {staff.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="flex flex-col gap-2 font-bold">
          {t("repeat")}
          <select
            value={repeat}
            onChange={(e) => setRepeat(Number(e.target.value))}
            className="border-trait bg-carte rounded-field min-h-12 border-2 px-3"
          >
            {[0, 1, 3, 7, 11].map((weeks) => (
              <option key={weeks} value={weeks}>
                {weeks === 0 ? t("once") : t("weeks", { count: weeks + 1 })}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Button type="submit" size="lg" disabled={busy || !valid}>
        <Plus aria-hidden size={24} weight="bold" />
        {t("open")}
      </Button>
    </form>
  );
}

const WEEK = [0, 1, 2, 3, 4, 5, 6];

function PlaceRow({ place }: { place: Place }) {
  const t = useTranslations("proSpace.slots");
  const locale = useLocale();
  const run = useRun();
  const [weekday, setWeekday] = useState(0);
  const [from, setFrom] = useState("09:00");
  const [to, setTo] = useState("13:00");
  const hours = place.hours;
  const save = (rows: typeof hours, message: string) =>
    run(
      () =>
        setPlaceHours(
          place.id,
          rows.map(({ weekday, starts_at, ends_at }) => ({ weekday, starts_at, ends_at })),
        ),
      message,
    );
  return (
    <li className="border-trait flex flex-col gap-3 border-b pb-4 last:border-b-0 last:pb-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-bold">{place.name}</p>
          <p className="text-prune-doux">
            {[place.address, place.district, place.city].filter(Boolean).join(", ")}
          </p>
        </div>
        <Button
          variant="quiet"
          onClick={() => void run(() => removePlace(place.id), t("placeRemoved"))}
        >
          <Trash aria-hidden size={22} />
          {t("remove")}
        </Button>
      </div>
      {hours.length === 0 ? (
        <p className="text-prune-doux">{t("placeNoHours")}</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {hours.map((row, index) => (
            <li
              key={`${row.weekday}-${row.starts_at}`}
              className="flex items-center justify-between gap-2"
            >
              <span>
                {weekdayName(row.weekday, locale)} : {row.starts_at} - {row.ends_at}
              </span>
              <Button
                variant="quiet"
                onClick={() =>
                  void save(
                    hours.filter((_, i) => i !== index),
                    t("saved"),
                  )
                }
              >
                {t("remove")}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
        <label className="flex flex-col gap-2 font-bold">
          {t("day")}
          <select
            value={weekday}
            onChange={(e) => setWeekday(Number(e.target.value))}
            className="border-trait bg-carte rounded-field min-h-12 border-2 px-3"
          >
            {WEEK.map((value) => (
              <option key={value} value={value}>
                {weekdayName(value, locale)}
              </option>
            ))}
          </select>
        </label>
        <Input
          label={t("from")}
          type="time"
          step={300}
          value={from}
          onChange={(e) => setFrom(e.target.value)}
        />
        <Input
          label={t("to")}
          type="time"
          step={300}
          value={to}
          onChange={(e) => setTo(e.target.value)}
        />
        <Button
          variant="secondary"
          disabled={minutes(to) <= minutes(from)}
          onClick={() =>
            void save(
              [...hours, { weekday, starts_at: from, ends_at: to, staff_id: null }],
              t("saved"),
            )
          }
        >
          {t("addHours")}
        </Button>
      </div>
    </li>
  );
}

function AddPlace() {
  const t = useTranslations("proSpace.slots");
  const run = useRun();
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [address, setAddress] = useState("");
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        void run(
          () => addPlace({ name: name.trim(), city, district, address }),
          t("placeAdded"),
        ).then((ok) => {
          if (ok) {
            setName("");
            setCity("");
            setDistrict("");
            setAddress("");
          }
        });
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label={t("placeName")}
          value={name}
          maxLength={80}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label={t("city")}
          value={city}
          maxLength={80}
          onChange={(e) => setCity(e.target.value)}
        />
        <Input
          label={t("district")}
          value={district}
          maxLength={80}
          onChange={(e) => setDistrict(e.target.value)}
        />
        <Input
          label={t("address")}
          value={address}
          maxLength={200}
          onChange={(e) => setAddress(e.target.value)}
        />
      </div>
      <Button type="submit" variant="secondary" disabled={!name.trim()}>
        <Plus aria-hidden size={22} weight="bold" />
        {t("addPlace")}
      </Button>
    </form>
  );
}

/** Everything about her time: how free times are made, the times she opens, where she works. */
export function AvailabilityScreen() {
  const t = useTranslations("proSpace.slots");
  const locale = useLocale();
  const run = useRun();
  const settings = useQuery({ queryKey: ["agenda-settings"], queryFn: getAgendaSettings });
  const agenda = useQuery({ queryKey: ["agenda", "slots"], queryFn: () => getAgenda({ days: 1 }) });
  const slots = useQuery({ queryKey: ["availability", "slots"], queryFn: () => getManualSlots() });
  const places = useQuery({ queryKey: ["availability", "places"], queryFn: getPlaces });

  if (settings.isPending || agenda.isPending) return <Skeleton className="rounded-card h-96" />;
  const data = settings.data;
  const zone = agenda.data?.pro.timezone;
  if (!data || !zone) return <p className="text-alerte font-bold">{t("error")}</p>;
  const change = (body: Parameters<typeof updateAgendaSettings>[0]) =>
    void run(() => updateAgendaSettings(body), t("saved"));

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-display">{t("title")}</h1>
          <p className="text-prune-doux">{t("line")}</p>
        </div>
        <SpeakButton text={t("title")} />
      </header>

      <Part
        id="mode-title"
        icon={<Clock size={26} weight="duotone" />}
        title={t("modeTitle")}
        help={t("modeHelp")}
      >
        <fieldset className="flex flex-col gap-2">
          <legend className="sr-only">{t("modeTitle")}</legend>
          {(["hours", "manual"] as const).map((mode) => (
            <label
              key={mode}
              className="border-trait has-checked:border-prune rounded-field flex min-h-14 cursor-pointer items-start gap-3 border-2 p-3"
            >
              <input
                type="radio"
                name="slot-mode"
                checked={data.slot_mode === mode}
                onChange={() => change({ slot_mode: mode })}
                className="mt-1 size-5"
              />
              <span>
                <span className="block font-bold">{t(`mode.${mode}`)}</span>
                <span className="text-prune-doux block">{t(`mode.${mode}Help`)}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <div className="flex flex-col gap-1 sm:flex-row sm:gap-6">
          <Link
            href="/pro/hours"
            className="inline-flex min-h-12 items-center gap-2 font-semibold underline"
          >
            <ArrowRight aria-hidden size={20} />
            {t("editHours")}
          </Link>
          <Link
            href="/pro/agenda/settings"
            className="inline-flex min-h-12 items-center gap-2 font-semibold underline"
          >
            <ArrowRight aria-hidden size={20} />
            {t("editTeam")}
          </Link>
        </div>
      </Part>

      <Part
        id="opened-title"
        icon={<Plus size={26} weight="bold" />}
        title={t("openedTitle")}
        help={t("openedHelp")}
      >
        <OpenSlotForm zone={zone} places={places.data ?? []} staff={agenda.data?.staff ?? []} />
        {slots.data && slots.data.length > 0 ? (
          <ul className="flex flex-col">
            {slots.data.map((slot) => (
              <li
                key={slot.id}
                className="border-trait flex items-center justify-between gap-3 border-t py-2"
              >
                <span className="min-w-0">
                  <span className="block font-semibold">
                    {dayName(localDay(slot.starts_at, zone), locale)},{" "}
                    {timeAt(slot.starts_at, zone, locale)} - {timeAt(slot.ends_at, zone, locale)}
                  </span>
                  <span className="text-small text-prune-doux block">
                    {[slot.place_name, slot.staff_name, slot.note].filter(Boolean).join(", ")}
                  </span>
                </span>
                <Button
                  variant="quiet"
                  onClick={() => void run(() => closeManualSlot(slot.id), t("closed"))}
                >
                  <Trash aria-hidden size={22} />
                  {t("remove")}
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-prune-doux">{t("openedEmpty")}</p>
        )}
      </Part>

      <Part
        id="block-title"
        icon={<CalendarX size={26} weight="duotone" />}
        title={t("blockTitle")}
        help={t("blockHelp")}
      >
        <Link
          href="/pro/agenda"
          className="inline-flex min-h-12 items-center gap-2 font-semibold underline"
        >
          <ArrowRight aria-hidden size={20} />
          {t("blockCta")}
        </Link>
      </Part>

      <Part id="rules-title" icon={<Timer size={26} weight="duotone" />} title={t("rulesTitle")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            key={`buffer-${data.buffer_minutes}`}
            label={t("buffer")}
            hint={t("bufferHint")}
            type="number"
            min={0}
            max={240}
            defaultValue={data.buffer_minutes}
            onBlur={(e) => change({ buffer_minutes: Number(e.target.value) || 0 })}
          />
          <Input
            key={`travel-${data.travel_minutes}`}
            label={t("travel")}
            hint={t("travelHint")}
            type="number"
            min={0}
            max={480}
            defaultValue={data.travel_minutes}
            onBlur={(e) => change({ travel_minutes: Number(e.target.value) || 0 })}
          />
        </div>
      </Part>

      <Part
        id="places-title"
        icon={<MapPin size={26} weight="duotone" />}
        title={t("placesTitle")}
        help={t("placesHelp")}
      >
        <div className="flex flex-col gap-1 sm:flex-row sm:gap-6">
          <Link
            href="/pro/place"
            className="inline-flex min-h-12 items-center gap-2 font-semibold underline"
          >
            <MapPin aria-hidden size={20} />
            {t("mainAddress")}
          </Link>
          <Link
            href="/pro/place"
            className="inline-flex min-h-12 items-center gap-2 font-semibold underline"
          >
            <Van aria-hidden size={20} />
            {t("homeVisits")}
          </Link>
        </div>
        {places.data && places.data.length > 0 && (
          <ul className="flex flex-col gap-4">
            {places.data.map((place) => (
              <PlaceRow key={place.id} place={place} />
            ))}
          </ul>
        )}
        <AddPlace />
      </Part>

      <Part
        id="pause-title"
        icon={<PauseCircle size={26} weight="duotone" />}
        title={t("pauseTitle")}
        help={t("pauseHelp")}
      >
        <Button
          variant={data.online_paused ? "primary" : "secondary"}
          onClick={() => change({ online_paused: !data.online_paused })}
        >
          {data.online_paused ? t("resume") : t("pause")}
        </Button>
      </Part>
    </div>
  );
}
