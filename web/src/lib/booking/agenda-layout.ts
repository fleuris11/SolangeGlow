/**
 * Where things go in the agenda grid: one column per person (day view) or per day (week
 * view), minutes from local midnight in the pro's zone. Pure functions, tested.
 */
import type { Agenda, Appointment, TimeOff } from "@/lib/api/booking";

import { localDay, minutesOfDay, weekdayOf } from "./time";

export type Column = { key: string; day: string; staffId: string };

export type Segment = { start: number; end: number; waiting: boolean };

export type Block = {
  key: string;
  appointment: Appointment;
  column: string;
  start: number;
  end: number;
  segments: Segment[];
};

export type Shade = { key: string; column: string; start: number; end: number; label?: string };

export const BLOCKING: Appointment["status"][] = [
  "pending",
  "awaiting_deposit",
  "confirmed",
  "proposed",
  "held",
];

const columnOf = (columns: Column[], day: string, staffId: string | null) =>
  columns.find((c) => c.day === day && c.staffId === staffId);

/**
 * Blocks of the appointments: the steps of one person are drawn together; a waiting step
 * (colour that acts) stays in the column of the person before it, lighter.
 */
export function blocksFor(appointments: Appointment[], columns: Column[], zone: string): Block[] {
  const blocks: Block[] = [];
  for (const appointment of appointments) {
    if (appointment.status === "expired") continue;
    const groups = new Map<string, Segment[]>();
    let owner: string | null = null;
    const steps = [...appointment.steps].sort((a, b) => a.position - b.position);
    for (const step of steps) {
      const staff = step.staff_id ?? owner;
      if (step.staff_id) owner = step.staff_id;
      if (!staff) continue;
      const day = localDay(step.starts_at, zone);
      const column = columnOf(columns, day, staff);
      if (!column) continue;
      const segment = {
        start: minutesOfDay(step.starts_at, zone),
        end: minutesOfDay(step.ends_at, zone) || 24 * 60,
        waiting: step.kind !== "work",
      };
      groups.set(column.key, [...(groups.get(column.key) ?? []), segment]);
    }
    for (const [column, segments] of groups) {
      blocks.push({
        key: `${appointment.id}:${column}`,
        appointment,
        column,
        start: Math.min(...segments.map((s) => s.start)),
        end: Math.max(...segments.map((s) => s.end)),
        segments,
      });
    }
  }
  return blocks;
}

type Hours = { weekday: number; starts_at: string; ends_at: string };

const toMinutes = (value: string) => {
  const [h, m] = value.split(":").map(Number) as [number, number];
  return h * 60 + m;
};

/** The working windows of a column (the person's own hours, or the salon's). */
export function workingWindows(agenda: Agenda, column: Column): [number, number][] {
  const staff = agenda.staff.find((s) => s.id === column.staffId);
  const weekday = weekdayOf(column.day);
  const rows: Hours[] = staff?.own_hours
    ? staff.periods
    : agenda.opening.map((o) => ({
        weekday: o.weekday,
        starts_at: o.opens_at,
        ends_at: o.closes_at,
      }));
  const windows = rows
    .filter((r) => r.weekday === weekday)
    .map((r) => [toMinutes(r.starts_at), toMinutes(r.ends_at)] as [number, number]);
  const breaks = (staff?.breaks ?? [])
    .filter((b) => b.weekday === weekday)
    .map((b) => [toMinutes(b.starts_at), toMinutes(b.ends_at)] as [number, number]);
  return breaks.reduce<[number, number][]>(
    (result, [a, b]) =>
      result.flatMap(([s, e]) =>
        b <= s || a >= e
          ? [[s, e]]
          : ([s < a ? [s, a] : null, b < e ? [b, e] : null].filter(Boolean) as [number, number][]),
      ),
    windows,
  );
}

/** Closed hours, breaks and time off, drawn as grey ranges. */
export function shadesFor(
  agenda: Agenda,
  columns: Column[],
  range: [number, number],
  zone: string,
  timeOff: TimeOff[],
): Shade[] {
  const shades: Shade[] = [];
  for (const column of columns) {
    let cursor = range[0];
    for (const [start, end] of workingWindows(agenda, column).sort((a, b) => a[0] - b[0])) {
      if (start > cursor)
        shades.push({
          key: `${column.key}:c${cursor}`,
          column: column.key,
          start: cursor,
          end: start,
        });
      cursor = Math.max(cursor, end);
    }
    if (cursor < range[1])
      shades.push({
        key: `${column.key}:c${cursor}`,
        column: column.key,
        start: cursor,
        end: range[1],
      });
    for (const off of timeOff) {
      if (off.staff_id && off.staff_id !== column.staffId) continue;
      const startDay = localDay(off.starts_at, zone);
      const endDay = localDay(off.ends_at, zone);
      if (column.day < startDay || column.day > endDay) continue;
      shades.push({
        key: `${column.key}:${off.id}`,
        column: column.key,
        start: column.day === startDay ? minutesOfDay(off.starts_at, zone) : range[0],
        end: column.day === endDay ? minutesOfDay(off.ends_at, zone) || 24 * 60 : range[1],
        label: off.note || `kind:${off.kind}`,
      });
    }
  }
  return shades;
}

/** First and last hour shown: the opening hours, at least 8:00 to 20:00. */
export function gridRange(
  agenda: Agenda,
  appointments: Appointment[],
  zone: string,
): [number, number] {
  const hours = [
    ...agenda.opening.flatMap((o) => [toMinutes(o.opens_at), toMinutes(o.closes_at)]),
    ...agenda.staff.flatMap((s) =>
      s.periods.flatMap((p) => [toMinutes(p.starts_at), toMinutes(p.ends_at)]),
    ),
    ...appointments.flatMap((a) => [
      minutesOfDay(a.starts_at, zone),
      minutesOfDay(a.ends_at, zone),
    ]),
  ];
  const first = Math.min(8 * 60, ...hours);
  const last = Math.max(20 * 60, ...hours.filter((h) => h > 0));
  return [Math.floor(first / 60) * 60, Math.min(24 * 60, Math.ceil(last / 60) * 60)];
}

/** A drag of `pixels` in the grid, rounded to the agenda step. */
export function snapMinutes(pixels: number, pxPerMinute: number, step: number): number {
  return Math.round(pixels / pxPerMinute / step) * step;
}
