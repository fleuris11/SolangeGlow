"use client";

import {
  CalendarBlank,
  CaretLeft,
  CaretRight,
  Gear,
  HourglassMedium,
  Plus,
  UserList,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getAgenda, moveAppointment, type Agenda, type Appointment } from "@/lib/api/booking";
import {
  blocksFor,
  gridRange,
  shadesFor,
  snapMinutes,
  type Block,
  type Column,
} from "@/lib/booking/agenda-layout";
import {
  addDays,
  dayName,
  localDay,
  minutesOfDay,
  mondayOf,
  timeAt,
  zonedToIso,
} from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { formatTimeOfDay } from "@/lib/time";

// Opened on demand (ADR-004): the sheets are not needed for the first view.
const AppointmentSheet = dynamic(() => import("./agenda-sheets").then((m) => m.AppointmentSheet));
const QuickSheet = dynamic(() => import("./agenda-sheets").then((m) => m.QuickSheet));

const PX = 1.6; // pixels per minute: one hour = 96 px
const HEADER = 56;

type View = "day" | "week";
type Drag = { block: Block; x: number; y: number; dx: number; dy: number; moved: boolean };

function today(zone: string) {
  return localDay(new Date(), zone);
}

/** The agenda: a day by person, or a week for one person; drag to move, tap to add. */
export function AgendaScreen({ initialDay }: { initialDay?: string }) {
  const t = useTranslations("booking.agenda");
  const tStatus = useTranslations("booking.status");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [view, setView] = useState<View>("day");
  const [day, setDay] = useState<string | undefined>(initialDay);
  const [person, setPerson] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [quick, setQuick] = useState<{ day: string; minutes: number; staffId: string } | null>(
    null,
  );
  const [drag, setDrag] = useState<Drag | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);
  const dragged = useRef(false);

  // The first answer tells the pro's zone; the day defaults to today there.
  const first = view === "week" && day ? mondayOf(day) : day;
  const query = useQuery({
    queryKey: ["agenda", view, first ?? "today"],
    queryFn: () =>
      getAgenda({
        start: first ?? new Date().toISOString().slice(0, 10),
        days: view === "week" ? 7 : 1,
      }),
    retry: false,
  });
  const agenda = query.data;
  const zone = agenda?.pro.timezone ?? "Africa/Porto-Novo";
  const shownDay = day ?? (agenda ? today(zone) : undefined);

  // Live: a booking, a cancellation, a colleague's move: read the days again.
  useEffect(() => {
    if (!agenda) return;
    let stop: (() => void) | undefined;
    let cancelled = false;
    void import("@/lib/booking/agenda-socket").then(({ connectAgenda }) => {
      if (cancelled) return;
      stop = connectAgenda(
        () => void queryClient.invalidateQueries({ queryKey: ["agenda"] }),
        agenda.pro.id,
      );
    });
    return () => {
      cancelled = true;
      stop?.();
    };
  }, [agenda?.pro.id, queryClient]); // eslint-disable-line react-hooks/exhaustive-deps

  const columns: Column[] = useMemo(() => {
    if (!agenda || !shownDay) return [];
    const staff = agenda.staff.filter((s) => s.is_active);
    if (view === "week") {
      const who = person ?? staff[0]?.id;
      if (!who) return [];
      const monday = mondayOf(shownDay);
      return Array.from({ length: 7 }, (_, i) => {
        const d = addDays(monday, i);
        return { key: d, day: d, staffId: who };
      });
    }
    return staff
      .filter((s) => !person || s.id === person)
      .map((s) => ({ key: s.id, day: shownDay, staffId: s.id }));
  }, [agenda, shownDay, view, person]);

  if (query.isError) {
    const code = query.error instanceof ApiError ? query.error.code : "";
    return (
      <EmptyState
        icon={<CalendarBlank size={44} weight="duotone" />}
        title={code === "agenda_not_found" ? t("noAgenda") : t("error")}
        description={code === "agenda_not_found" ? t("noAgendaHelp") : undefined}
        action={
          code === "agenda_not_found" ? (
            <Link href="/pro/start" className={buttonClasses({ size: "lg" })}>
              {t("becomePro")}
            </Link>
          ) : undefined
        }
      />
    );
  }
  if (!agenda || !shownDay) return <Skeleton className="rounded-card h-96" />;

  const appointments = agenda.appointments;
  const range = gridRange(agenda, appointments, zone);
  const blocks = blocksFor(appointments, columns, zone);
  const shades = shadesFor(agenda, columns, range, zone, agenda.time_off);
  const height = (range[1] - range[0]) * PX;
  const step = agenda.slot_step_minutes;
  const pending = agenda.pending;
  const staffName = (id: string) => agenda.staff.find((s) => s.id === id)?.name ?? "";
  const color = (id: string) => agenda.staff.find((s) => s.id === id)?.color;
  const title =
    view === "week"
      ? t("weekOf", { day: dayName(mondayOf(shownDay), locale) })
      : dayName(shownDay, locale);

  const shift = (count: number) => setDay(addDays(shownDay, view === "week" ? count * 7 : count));

  const columnAt = (clientX: number): Column | undefined => {
    const grid = gridRef.current;
    if (!grid) return undefined;
    const cells = grid.querySelectorAll<HTMLElement>("[data-column]");
    for (const cell of cells) {
      const box = cell.getBoundingClientRect();
      if (clientX >= box.left && clientX < box.right) {
        return columns.find((c) => c.key === cell.dataset.column);
      }
    }
    return undefined;
  };

  const startDrag = (event: ReactPointerEvent, block: Block) => {
    if (!agenda.can_manage && block.appointment.status !== "confirmed") return;
    (event.target as HTMLElement).setPointerCapture?.(event.pointerId);
    setDrag({ block, x: event.clientX, y: event.clientY, dx: 0, dy: 0, moved: false });
  };

  const moveDrag = (event: ReactPointerEvent) => {
    if (!drag) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    setDrag({ ...drag, dx, dy, moved: drag.moved || Math.abs(dy) > 8 || Math.abs(dx) > 16 });
  };

  const endDrag = async (event: ReactPointerEvent) => {
    if (!drag) return;
    const current = drag;
    setDrag(null);
    if (!current.moved) return; // a tap: the click opens it
    dragged.current = true;
    const delta = snapMinutes(current.dy, PX, step);
    const target = columnAt(event.clientX) ?? columns.find((c) => c.key === current.block.column);
    if (!target) return;
    const source = columns.find((c) => c.key === current.block.column);
    const minutes = current.block.start + delta;
    const start = zonedToIso(target.day, minutes, zone);
    const staffChanged = source && target.staffId !== source.staffId;
    if (delta === 0 && !staffChanged && target.day === source?.day) return;
    try {
      await moveAppointment(
        current.block.appointment.id,
        start,
        staffChanged ? target.staffId : null,
      );
      toast(t("moved", { time: timeAt(start, zone, locale) }), "success");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      void queryClient.invalidateQueries({ queryKey: ["agenda"] });
    }
  };

  const tapGrid = (event: React.MouseEvent<HTMLDivElement>, column: Column) => {
    if (event.target !== event.currentTarget) return;
    const box = event.currentTarget.getBoundingClientRect();
    const minutes = range[0] + snapMinutes(event.clientY - box.top, PX, step);
    setQuick({ day: column.day, minutes, staffId: column.staffId });
  };

  const hours = Array.from({ length: (range[1] - range[0]) / 60 }, (_, i) => range[0] + i * 60);
  const nowMinutes = columns.some((c) => c.day === today(zone))
    ? minutesOfDay(new Date(), zone)
    : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={t("title")} />
      </div>
      {agenda.can_manage && (
        <div className="flex flex-wrap gap-2">
          <Link href="/pro/agenda/clients" className={buttonClasses({ variant: "secondary" })}>
            <UserList aria-hidden size={24} />
            {t("clients")}
          </Link>
          <Link href="/pro/agenda/settings" className={buttonClasses({ variant: "secondary" })}>
            <Gear aria-hidden size={24} />
            {t("settings")}
          </Link>
        </div>
      )}

      {pending.length > 0 && (
        <section
          aria-labelledby="pending"
          className="bg-poudre rounded-card flex flex-col gap-2 p-4"
        >
          <h2 id="pending" className="flex items-center gap-2 font-bold">
            <HourglassMedium aria-hidden size={24} weight="duotone" className="text-alerte" />
            {t("pending", { count: pending.length })}
          </h2>
          <ul className="flex flex-col gap-2">
            {pending.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  onClick={() => setOpen(a.id)}
                  className="bg-carte flex min-h-12 w-full items-center justify-between gap-2 rounded-2xl px-3 text-left"
                >
                  <span className="font-bold">{a.client_name}</span>
                  <span className="text-small">
                    {a.service_name}, {dayName(localDay(a.starts_at, zone), locale, true)}{" "}
                    {timeAt(a.starts_at, zone, locale)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div
          role="tablist"
          aria-label={t("view")}
          className="bg-poudre grid grid-cols-2 rounded-full p-1 sm:w-64"
        >
          {(["day", "week"] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={view === key}
              onClick={() => setView(key)}
              className={cn(
                "min-h-12 rounded-full px-4 font-bold",
                view === key ? "bg-carte text-prune" : "text-prune-doux",
              )}
            >
              {key === "day" ? t("day") : t("week")}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="quiet" aria-label={t("previous")} onClick={() => shift(-1)}>
            <CaretLeft aria-hidden size={24} />
          </Button>
          <Button variant="secondary" onClick={() => setDay(today(zone))}>
            {t("today")}
          </Button>
          <Button variant="quiet" aria-label={t("next")} onClick={() => shift(1)}>
            <CaretRight aria-hidden size={24} />
          </Button>
        </div>
      </div>
      <p className="text-lead font-bold first-letter:uppercase" aria-live="polite">
        {title}
      </p>

      {agenda.staff.length > 1 && (
        <div className="-mx-4 overflow-x-auto px-4" tabIndex={0} aria-label={t("people")}>
          <div className="flex gap-2">
            {view === "day" && (
              <button
                type="button"
                aria-pressed={person === null}
                onClick={() => setPerson(null)}
                className={cn(
                  "min-h-12 rounded-full border-2 px-4 font-bold whitespace-nowrap",
                  person === null
                    ? "border-hibiscus bg-hibiscus text-sur-hibiscus"
                    : "border-trait",
                )}
              >
                {t("everyone")}
              </button>
            )}
            {agenda.staff.map((s) => (
              <button
                key={s.id}
                type="button"
                aria-pressed={
                  person === s.id || (view === "week" && !person && s.id === columns[0]?.staffId)
                }
                onClick={() => setPerson(s.id)}
                className={cn(
                  "flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold whitespace-nowrap",
                  person === s.id || (view === "week" && !person && s.id === columns[0]?.staffId)
                    ? "border-hibiscus bg-poudre"
                    : "border-trait",
                )}
              >
                <span
                  aria-hidden
                  className="size-3 rounded-full"
                  style={{ backgroundColor: s.color }}
                />
                {s.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <div
        className="border-trait bg-carte rounded-card relative overflow-auto border"
        style={{ maxHeight: "70vh" }}
        tabIndex={0}
        aria-label={t("grid")}
      >
        <div
          ref={gridRef}
          className="relative flex"
          style={{ minWidth: columns.length > 1 ? columns.length * 140 + 56 : undefined }}
          onPointerMove={moveDrag}
          onPointerUp={(e) => void endDrag(e)}
          onPointerCancel={() => setDrag(null)}
        >
          <div className="bg-carte sticky left-0 z-20 w-14 shrink-0" aria-hidden>
            <div style={{ height: HEADER }} />
            <div className="relative" style={{ height }}>
              {hours.map((h) => (
                <span
                  key={h}
                  className="text-small text-prune-doux absolute right-1 -translate-y-2"
                  style={{ top: (h - range[0]) * PX }}
                >
                  {formatTimeOfDay(h / 60, 0, locale)}
                </span>
              ))}
            </div>
          </div>
          {columns.map((column) => (
            <div key={column.key} className="border-trait min-w-36 flex-1 border-l">
              <div
                className="bg-carte border-trait sticky top-0 z-10 flex flex-col justify-center border-b px-2"
                style={{ height: HEADER }}
              >
                {view === "week" ? (
                  <span className={cn("font-bold", column.day === today(zone) && "text-hibiscus")}>
                    {dayName(column.day, locale, true)}
                  </span>
                ) : (
                  <span className="flex items-center gap-2 font-bold">
                    <span
                      aria-hidden
                      className="size-3 rounded-full"
                      style={{ backgroundColor: color(column.staffId) }}
                    />
                    {staffName(column.staffId)}
                  </span>
                )}
              </div>
              <div
                data-column={column.key}
                className="relative cursor-cell"
                style={{
                  height,
                  backgroundImage:
                    "repeating-linear-gradient(to bottom, var(--trait) 0, var(--trait) 1px, transparent 1px, transparent 48px)",
                }}
                onClick={(e) => tapGrid(e, column)}
                role="presentation"
              >
                {shades
                  .filter((s) => s.column === column.key)
                  .map((s) => (
                    <div
                      key={s.key}
                      aria-hidden={!s.label}
                      className={cn(
                        "pointer-events-none absolute inset-x-0",
                        s.label ? "bg-poudre/80 text-small text-prune-doux p-1" : "bg-poudre/50",
                      )}
                      style={{ top: (s.start - range[0]) * PX, height: (s.end - s.start) * PX }}
                    >
                      {s.label?.startsWith("kind:")
                        ? t(`off.${s.label.slice(5) as "block"}`)
                        : s.label}
                    </div>
                  ))}
                {nowMinutes !== null && column.day === today(zone) && (
                  <div
                    aria-hidden
                    className="bg-hibiscus pointer-events-none absolute inset-x-0 z-10 h-0.5"
                    style={{ top: (nowMinutes - range[0]) * PX }}
                  />
                )}
                {blocks
                  .filter((b) => b.column === column.key)
                  .map((block) => {
                    const a = block.appointment;
                    const dragging = drag?.block.key === block.key && drag.moved;
                    const pendingLike =
                      a.status === "pending" ||
                      a.status === "awaiting_deposit" ||
                      a.status === "proposed" ||
                      a.status === "held";
                    const done = ![
                      "pending",
                      "awaiting_deposit",
                      "confirmed",
                      "proposed",
                      "held",
                    ].includes(a.status);
                    return (
                      <button
                        key={block.key}
                        type="button"
                        onPointerDown={(e) => startDrag(e, block)}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (dragged.current) {
                            dragged.current = false;
                            return;
                          }
                          setOpen(a.id);
                        }}
                        aria-label={t("blockLabel", {
                          client: a.client_name,
                          service: a.service_name,
                          time: timeAt(a.starts_at, zone, locale),
                          status: tStatus(a.status),
                        })}
                        className={cn(
                          "bg-carte absolute inset-x-1 touch-none overflow-hidden rounded-xl border-2 border-l-8 text-left select-none",
                          pendingLike ? "border-dashed" : "border-solid",
                          done && "opacity-60",
                          dragging && "z-30 shadow-lg",
                        )}
                        style={{
                          top: (block.start - range[0]) * PX + (dragging ? drag.dy : 0),
                          height: Math.max((block.end - block.start) * PX, 28),
                          transform: dragging ? `translateX(${drag.dx}px)` : undefined,
                          borderColor: color(
                            columns.find((c) => c.key === block.column)?.staffId ?? "",
                          ),
                        }}
                      >
                        {block.segments
                          .filter((s) => s.waiting)
                          .map((s, i) => (
                            <span
                              key={i}
                              aria-hidden
                              className="bg-poudre absolute inset-x-0"
                              style={{
                                top: (s.start - block.start) * PX,
                                height: (s.end - s.start) * PX,
                              }}
                            />
                          ))}
                        <span className="relative flex flex-col px-2 py-1">
                          <span className="text-small truncate font-bold">{a.client_name}</span>
                          <span className="text-small truncate">{a.service_name}</span>
                          {pendingLike && (
                            <span className="text-small text-alerte font-bold">
                              {tStatus(a.status)}
                            </span>
                          )}
                        </span>
                      </button>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <Button
        size="lg"
        fullWidth
        onClick={() =>
          setQuick({
            day: shownDay,
            minutes: Math.max(
              range[0],
              nowMinutes ? Math.ceil(nowMinutes / step) * step : range[0],
            ),
            staffId: columns[0]?.staffId ?? "",
          })
        }
      >
        <Plus aria-hidden size={26} weight="bold" />
        {t("add")}
      </Button>
      <p className="text-small text-prune-doux">{t("help")}</p>

      {open && (
        <AppointmentSheet
          id={open}
          zone={zone}
          canManage={agenda.can_manage}
          onClose={() => setOpen(null)}
        />
      )}
      {quick && (
        <QuickSheet
          agenda={agenda as Agenda}
          zone={zone}
          slot={quick}
          onClose={() => setQuick(null)}
        />
      )}
    </div>
  );
}

export type { Appointment };
