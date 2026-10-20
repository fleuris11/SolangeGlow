"use client";

import {
  ArrowLeft,
  CalendarCheck,
  Copy,
  Lightning,
  Package,
  Plus,
  QrCode,
  Trash,
  UserPlus,
  UsersThree,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  addResource,
  addStaff,
  BOOKING_QR_URL,
  getAgenda,
  getAgendaSettings,
  getStaff,
  removeResource,
  setLastMinute,
  setStaffHours,
  updateAgendaSettings,
  updateStaff,
  type AgendaSettings,
  type HoursRow,
  type Staff,
} from "@/lib/api/booking";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";

const PALETTE = [1, 2, 3, 4, 5, 6].map((n) => `agenda-${n}`);

/** The colours of the tokens (stored as #rrggbb with each person). */
function palette(): string[] {
  const style = getComputedStyle(document.documentElement);
  return PALETTE.map((name) => style.getPropertyValue(`--${name}`).trim().toUpperCase());
}
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];

function useRun() {
  const t = useTranslations("booking.settings");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const run = async (action: () => Promise<unknown>, done = t("saved")) => {
    setBusy(true);
    try {
      await action();
      toast(done, "success");
      await queryClient.invalidateQueries({ queryKey: ["agenda-settings"] });
      await queryClient.invalidateQueries({ queryKey: ["agenda-staff"] });
      await queryClient.invalidateQueries({ queryKey: ["agenda"] });
      return true;
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, run };
}

function Section({
  id,
  title,
  icon,
  children,
}: {
  id: string;
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      aria-labelledby={id}
      className="border-trait bg-carte rounded-card flex flex-col gap-4 border p-4"
    >
      <h2 id={id} className="text-title flex items-center gap-2 font-bold">
        <span aria-hidden className="text-hibiscus">
          {icon}
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

/** « Agenda settings »: the link to share, the rules, the team, the resources, last minute. */
export function AgendaSettingsScreen() {
  const t = useTranslations("booking.settings");
  const query = useQuery({
    queryKey: ["agenda-settings"],
    queryFn: getAgendaSettings,
    retry: false,
  });
  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  if (!query.data) {
    return (
      <p className="text-prune-doux">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const settings = query.data;
  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/pro/agenda"
        className="text-prune-doux hover:bg-poudre -ml-2 inline-flex min-h-12 items-center gap-2 self-start rounded-full px-2 font-bold"
      >
        <ArrowLeft aria-hidden size={22} />
        {t("back")}
      </Link>
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={t("title")} />
      </div>
      <ShareLink settings={settings} />
      <Rules settings={settings} />
      <Team />
      <Resources settings={settings} />
      <LastMinute settings={settings} />
    </div>
  );
}

function ShareLink({ settings }: { settings: AgendaSettings }) {
  const t = useTranslations("booking.settings");
  const toast = useToast();
  const copy = async (value: string) => {
    await navigator.clipboard?.writeText(value);
    toast(t("copied"), "success");
  };
  return (
    <Section id="link" title={t("link")} icon={<QrCode size={28} weight="duotone" />}>
      <p className="text-prune-doux">{t("linkHelp")}</p>
      <p className="bg-poudre rounded-2xl p-3 font-bold break-all">{settings.booking_url}</p>
      <Button variant="secondary" fullWidth onClick={() => void copy(settings.booking_url)}>
        <Copy aria-hidden size={24} />
        {t("copy")}
      </Button>
      {/* eslint-disable-next-line @next/next/no-img-element -- a PNG drawn by the backend */}
      <img
        src={BOOKING_QR_URL}
        alt={t("qrAlt")}
        width={200}
        height={200}
        className="self-center rounded-2xl"
      />
      <a
        href={`${BOOKING_QR_URL}?download=1`}
        className={buttonClasses({ variant: "secondary", fullWidth: true })}
      >
        {t("downloadQr")}
      </a>
      <details className="flex flex-col gap-2">
        <summary className="min-h-12 cursor-pointer py-3 font-bold">{t("ical")}</summary>
        <p className="text-small text-prune-doux">{t("icalHelp")}</p>
        <p className="bg-poudre text-small rounded-2xl p-3 break-all">{settings.ical_url}</p>
        <Button variant="quiet" fullWidth onClick={() => void copy(settings.ical_url)}>
          <Copy aria-hidden size={24} />
          {t("copy")}
        </Button>
      </details>
    </Section>
  );
}

function NumberField({
  label,
  hint,
  value,
  placeholder,
  onSave,
}: {
  label: string;
  hint: string;
  value: number | null | undefined;
  placeholder: number;
  onSave: (value: number | null) => void;
}) {
  const [text, setText] = useState(value === null || value === undefined ? "" : String(value));
  return (
    <Input
      label={label}
      hint={hint}
      inputMode="numeric"
      value={text}
      placeholder={String(placeholder)}
      onChange={(e) => setText(e.target.value.replace(/[^\d]/g, ""))}
      onBlur={() => {
        const next = text === "" ? null : Number(text);
        if (next !== (value ?? null)) onSave(next);
      }}
    />
  );
}

function Rules({ settings }: { settings: AgendaSettings }) {
  const t = useTranslations("booking.settings");
  const { run } = useRun();
  const save = (body: Parameters<typeof updateAgendaSettings>[0]) =>
    void run(() => updateAgendaSettings(body));
  return (
    <Section id="rules" title={t("rules")} icon={<CalendarCheck size={28} weight="duotone" />}>
      <SwitchRow
        icon={<CalendarCheck size={26} weight="duotone" />}
        label={t("autoConfirm")}
        description={t("autoConfirmHelp")}
        checked={settings.auto_confirm}
        onChange={(value) => save({ auto_confirm: value })}
      />
      <SwitchRow
        icon={<UsersThree size={26} weight="duotone" />}
        label={t("guests")}
        description={t("guestsHelp")}
        checked={settings.accepts_guests}
        onChange={(value) => save({ accepts_guests: value })}
      />
      <label className="flex flex-col gap-2 font-bold">
        {t("step")}
        <select
          value={settings.slot_step_minutes}
          onChange={(e) => save({ slot_step_minutes: Number(e.target.value) })}
          className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
        >
          {[10, 15, 20, 30, 45, 60].map((m) => (
            <option key={m} value={m}>
              {t("minutes", { count: m })}
            </option>
          ))}
        </select>
      </label>
      <NumberField
        label={t("notice")}
        hint={t("noticeHelp")}
        value={settings.min_notice_minutes}
        placeholder={settings.defaults.min_notice_minutes}
        onSave={(value) => save({ min_notice_minutes: value })}
      />
      <NumberField
        label={t("horizon")}
        hint={t("horizonHelp")}
        value={settings.horizon_days}
        placeholder={settings.defaults.horizon_days}
        onSave={(value) => save({ horizon_days: value })}
      />
      <NumberField
        label={t("freeCancel")}
        hint={t("freeCancelHelp")}
        value={settings.free_cancel_hours}
        placeholder={settings.defaults.free_cancel_hours}
        onSave={(value) => save({ free_cancel_hours: value })}
      />
      <NumberField
        label={t("late")}
        hint={t("lateHelp")}
        value={settings.late_tolerance_minutes}
        placeholder={settings.defaults.late_tolerance_minutes}
        onSave={(value) => save({ late_tolerance_minutes: value })}
      />
    </Section>
  );
}

function Team() {
  const t = useTranslations("booking.settings");
  const query = useQuery({ queryKey: ["agenda-staff"], queryFn: getStaff });
  const [editing, setEditing] = useState<Staff | "new" | null>(null);
  return (
    <Section id="team" title={t("team")} icon={<UsersThree size={28} weight="duotone" />}>
      <p className="text-prune-doux">{t("teamHelp")}</p>
      {query.isPending ? (
        <Skeleton className="h-24 rounded-2xl" />
      ) : (
        <ul className="flex flex-col gap-2">
          {(query.data ?? []).map((member) => (
            <li key={member.id}>
              <button
                type="button"
                onClick={() => setEditing(member)}
                className="border-trait hover:bg-poudre flex min-h-16 w-full items-center gap-3 rounded-2xl border p-3 text-left"
              >
                <span
                  aria-hidden
                  className="size-4 shrink-0 rounded-full"
                  style={{ backgroundColor: member.color }}
                />
                <span className="flex flex-1 flex-col">
                  <span className="font-bold">{member.name}</span>
                  <span className="text-small text-prune-doux">
                    {member.is_owner
                      ? t("you")
                      : member.has_account
                        ? t("linked")
                        : member.phone
                          ? t("invited")
                          : t("noAccount")}
                    {!member.is_active && `, ${t("inactive")}`}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <Button variant="secondary" fullWidth onClick={() => setEditing("new")}>
        <UserPlus aria-hidden size={24} />
        {t("addPerson")}
      </Button>
      {editing && (
        <PersonSheet member={editing === "new" ? null : editing} onClose={() => setEditing(null)} />
      )}
    </Section>
  );
}

function PersonSheet({ member, onClose }: { member: Staff | null; onClose: () => void }) {
  const t = useTranslations("booking.settings");
  const tDays = useTranslations("booking.weekdays");
  const { busy, run } = useRun();
  const services = useQuery({
    queryKey: ["agenda", "services"],
    queryFn: () => getAgenda({ start: new Date().toISOString().slice(0, 10), days: 1 }),
  });
  const [name, setName] = useState(member?.name ?? "");
  const [phone, setPhone] = useState(member?.phone ?? "");
  const [colors] = useState(palette);
  const [color, setColor] = useState(member?.color ?? colors[1] ?? "");
  const [serviceIds, setServiceIds] = useState<string[]>(member?.service_ids ?? []);
  const [limit, setLimit] = useState(member?.daily_limit ? String(member.daily_limit) : "");
  const [ownHours, setOwnHours] = useState(member?.own_hours ?? false);
  const [active, setActive] = useState(member?.is_active ?? true);
  const [periods, setPeriods] = useState<HoursRow[]>(member?.periods ?? []);

  const save = async () => {
    const body = {
      name,
      color,
      phone,
      service_ids: serviceIds,
      daily_limit: limit ? Number(limit) : null,
      own_hours: ownHours,
      is_active: active,
    };
    const ok = await run(async () => {
      const saved = member ? await updateStaff(member.id, body) : await addStaff(body);
      if (ownHours) await setStaffHours(saved.id, { periods });
    });
    if (ok) onClose();
  };

  const rowFor = (weekday: number) => periods.find((p) => p.weekday === weekday);
  const setRow = (weekday: number, row: HoursRow | null) =>
    setPeriods((rows) => [...rows.filter((r) => r.weekday !== weekday), ...(row ? [row] : [])]);

  return (
    <Sheet
      open
      onOpenChange={(value) => !value && onClose()}
      title={member ? member.name : t("addPerson")}
    >
      <div className="flex flex-col gap-4">
        <Input
          label={t("personName")}
          value={name}
          maxLength={80}
          onChange={(e) => setName(e.target.value)}
        />
        {!member?.is_owner && (
          <Input
            label={t("personPhone")}
            hint={t("personPhoneHelp")}
            inputMode="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        )}
        <fieldset className="flex flex-col gap-2">
          <legend className="font-bold">{t("color")}</legend>
          <div className="flex flex-wrap gap-3">
            {colors.map((value, i) => (
              <button
                key={value}
                type="button"
                aria-pressed={color === value}
                aria-label={t("colorNumber", { number: i + 1 })}
                onClick={() => setColor(value)}
                className={cn(
                  "size-12 rounded-full border-4",
                  color === value ? "border-prune" : "border-transparent",
                )}
                style={{ backgroundColor: `var(--${PALETTE[i]})` }}
              />
            ))}
          </div>
        </fieldset>
        <fieldset className="flex flex-col gap-2">
          <legend className="font-bold">{t("services")}</legend>
          <p className="text-small text-prune-doux">{t("servicesHelp")}</p>
          {(services.data?.services ?? []).map((service) => (
            <label key={service.id} className="flex min-h-12 items-center gap-3">
              <input
                type="checkbox"
                className="accent-hibiscus size-6"
                checked={serviceIds.includes(service.id)}
                onChange={(e) =>
                  setServiceIds((ids) =>
                    e.target.checked ? [...ids, service.id] : ids.filter((id) => id !== service.id),
                  )
                }
              />
              {service.name}
            </label>
          ))}
        </fieldset>
        <Input
          label={t("limit")}
          hint={t("limitHelp")}
          inputMode="numeric"
          value={limit}
          onChange={(e) => setLimit(e.target.value.replace(/[^\d]/g, ""))}
        />
        <SwitchRow
          icon={<CalendarCheck size={26} weight="duotone" />}
          label={t("ownHours")}
          description={t("ownHoursHelp")}
          checked={ownHours}
          onChange={setOwnHours}
        />
        {ownHours && (
          <ul className="flex flex-col gap-2">
            {WEEKDAYS.map((weekday) => {
              const row = rowFor(weekday);
              return (
                <li key={weekday} className="flex flex-wrap items-center gap-2">
                  <label className="flex min-h-12 w-32 items-center gap-2 font-bold">
                    <input
                      type="checkbox"
                      className="accent-hibiscus size-6"
                      checked={!!row}
                      onChange={(e) =>
                        setRow(
                          weekday,
                          e.target.checked
                            ? { weekday, starts_at: "09:00", ends_at: "18:00" }
                            : null,
                        )
                      }
                    />
                    {tDays(String(weekday) as "0")}
                  </label>
                  {row && (
                    <>
                      <input
                        type="time"
                        aria-label={t("from", { day: tDays(String(weekday) as "0") })}
                        value={row.starts_at}
                        onChange={(e) => setRow(weekday, { ...row, starts_at: e.target.value })}
                        className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-2"
                      />
                      <input
                        type="time"
                        aria-label={t("to", { day: tDays(String(weekday) as "0") })}
                        value={row.ends_at}
                        onChange={(e) => setRow(weekday, { ...row, ends_at: e.target.value })}
                        className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-2"
                      />
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {member && !member.is_owner && (
          <SwitchRow
            icon={<UsersThree size={26} weight="duotone" />}
            label={t("active")}
            description={t("activeHelp")}
            checked={active}
            onChange={setActive}
          />
        )}
        <Button size="lg" fullWidth disabled={busy || !name.trim()} onClick={() => void save()}>
          {t("savePerson")}
        </Button>
      </div>
    </Sheet>
  );
}

function Resources({ settings }: { settings: AgendaSettings }) {
  const t = useTranslations("booking.settings");
  const { busy, run } = useRun();
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("1");
  return (
    <Section id="resources" title={t("resources")} icon={<Package size={28} weight="duotone" />}>
      <p className="text-prune-doux">{t("resourcesHelp")}</p>
      {settings.resources.length > 0 && (
        <ul className="flex flex-col gap-2">
          {settings.resources.map((resource) => (
            <li
              key={resource.id}
              className="border-trait flex min-h-12 items-center gap-2 rounded-2xl border p-2 pl-4"
            >
              <span className="flex-1 font-bold">
                {resource.name} ({resource.quantity})
              </span>
              <Button
                variant="quiet"
                aria-label={t("remove", { name: resource.name })}
                disabled={busy}
                onClick={() => void run(() => removeResource(resource.id))}
              >
                <Trash aria-hidden size={22} />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="grid grid-cols-[1fr_6rem] gap-3">
        <Input
          label={t("resourceName")}
          value={name}
          maxLength={60}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label={t("quantity")}
          inputMode="numeric"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value.replace(/[^\d]/g, ""))}
        />
      </div>
      <Button
        variant="secondary"
        fullWidth
        disabled={busy || !name.trim() || !Number(quantity)}
        onClick={() =>
          void run(() => addResource({ name, quantity: Number(quantity) })).then(
            (ok) => ok && setName(""),
          )
        }
      >
        <Plus aria-hidden size={24} />
        {t("addResource")}
      </Button>
    </Section>
  );
}

function LastMinute({ settings }: { settings: AgendaSettings }) {
  const t = useTranslations("booking.settings");
  const { busy, run } = useRun();
  const current = settings.last_minute;
  const [percent, setPercent] = useState(String(current?.percent_off ?? 20));
  const [hours, setHours] = useState(String(current?.window_hours ?? 24));
  const save = (is_active: boolean) =>
    void run(
      () => setLastMinute({ percent_off: Number(percent), window_hours: Number(hours), is_active }),
      is_active ? t("lastMinuteOn") : t("saved"),
    );
  return (
    <Section
      id="last-minute"
      title={t("lastMinute")}
      icon={<Lightning size={28} weight="duotone" />}
    >
      <p className="text-prune-doux">{t("lastMinuteHelp")}</p>
      <div className="grid grid-cols-2 gap-3">
        <Input
          label={t("percent")}
          inputMode="numeric"
          value={percent}
          onChange={(e) => setPercent(e.target.value.replace(/[^\d]/g, ""))}
        />
        <Input
          label={t("window")}
          inputMode="numeric"
          value={hours}
          onChange={(e) => setHours(e.target.value.replace(/[^\d]/g, ""))}
        />
      </div>
      {current?.is_active ? (
        <>
          <p className="text-feuille font-bold" role="status">
            {t("lastMinuteActive", { percent: current.percent_off, hours: current.window_hours })}
          </p>
          <Button variant="secondary" fullWidth disabled={busy} onClick={() => save(true)}>
            {t("update")}
          </Button>
          <Button variant="quiet" fullWidth disabled={busy} onClick={() => save(false)}>
            {t("stop")}
          </Button>
        </>
      ) : (
        <Button size="lg" fullWidth disabled={busy} onClick={() => save(true)}>
          <Lightning aria-hidden size={24} weight="bold" />
          {t("start")}
        </Button>
      )}
    </Section>
  );
}
