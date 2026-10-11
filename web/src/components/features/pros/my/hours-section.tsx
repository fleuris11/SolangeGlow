"use client";

import { CalendarX, FloppyDisk, Plus, Trash } from "@phosphor-icons/react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { addClosure, deleteClosure, myProQueryKey, saveMyHours, type MyPro } from "@/lib/api/pros";
import { weekdayName } from "@/lib/pros/format";

import { fieldClass, SectionFrame } from "./section-frame";

type Day = { open: boolean; spans: { from: string; to: string }[] };

function weekOf(pro: MyPro): Day[] {
  return Array.from({ length: 7 }, (_, weekday) => {
    const spans = pro.hours
      .filter((period) => period.weekday === weekday)
      .map((period) => ({ from: period.opens_at, to: period.closes_at }));
    return {
      open: spans.length > 0,
      spans: spans.length ? spans : [{ from: "09:00", to: "18:00" }],
    };
  });
}

/** Opening hours day by day (a break = two periods), and exceptional closures. */
export function HoursSection({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.hours");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [week, setWeek] = useState<Day[]>(() => weekOf(pro));
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [closure, setClosure] = useState({ starts_on: "", ends_on: "", reason: "" });

  const change = (weekday: number, day: Day) =>
    setWeek((current) => current.map((item, index) => (index === weekday ? day : item)));

  const refresh = () => queryClient.invalidateQueries({ queryKey: myProQueryKey });

  const save = async () => {
    setBusy(true);
    setError(undefined);
    try {
      await saveMyHours(
        week.flatMap((day, weekday) =>
          day.open
            ? day.spans.map((span) => ({
                weekday: weekday as 0,
                opens_at: span.from,
                closes_at: span.to,
              }))
            : [],
        ),
      );
      await refresh();
      toast(t("saved"), "success");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  const copyMonday = () =>
    setWeek((current) =>
      current.map((day, index) => (index === 0 || index === 6 ? day : { ...current[0]! })),
    );

  const addOne = async () => {
    setError(undefined);
    try {
      await addClosure({ ...closure, ends_on: closure.ends_on || closure.starts_on });
      setClosure({ starts_on: "", ends_on: "", reason: "" });
      await refresh();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    }
  };

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <ul className="flex flex-col gap-3">
        {week.map((day, weekday) => (
          <li
            key={weekday}
            className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="font-bold">{weekdayName(weekday, locale)}</span>
              <Button
                variant={day.open ? "secondary" : "quiet"}
                aria-pressed={day.open}
                onClick={() => change(weekday, { ...day, open: !day.open })}
              >
                {day.open ? t("open") : t("closed")}
              </Button>
            </div>
            {day.open && (
              <>
                {day.spans.map((span, index) => (
                  <div key={index} className="grid grid-cols-2 gap-3">
                    {(["from", "to"] as const).map((edge) => (
                      <label key={edge} className="flex flex-col gap-1">
                        <span className="text-small font-bold">{t(edge)}</span>
                        <input
                          type="time"
                          value={span[edge]}
                          step={900}
                          onChange={(event) =>
                            change(weekday, {
                              ...day,
                              spans: day.spans.map((item, i) =>
                                i === index ? { ...item, [edge]: event.target.value } : item,
                              ),
                            })
                          }
                          className={fieldClass}
                        />
                      </label>
                    ))}
                  </div>
                ))}
                {day.spans.length === 1 ? (
                  <Button
                    variant="quiet"
                    onClick={() =>
                      change(weekday, {
                        ...day,
                        spans: [
                          { from: day.spans[0]!.from, to: "12:00" },
                          { from: "14:00", to: day.spans[0]!.to },
                        ],
                      })
                    }
                  >
                    <Plus aria-hidden size={20} />
                    {t("addBreak")}
                  </Button>
                ) : (
                  <Button
                    variant="quiet"
                    onClick={() =>
                      change(weekday, {
                        ...day,
                        spans: [{ from: day.spans[0]!.from, to: day.spans.at(-1)!.to }],
                      })
                    }
                  >
                    <Trash aria-hidden size={20} />
                    {t("removeBreak")}
                  </Button>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
      <Button variant="secondary" onClick={copyMonday}>
        {t("copyMonday")}
      </Button>
      {error && (
        <p role="alert" className="text-alerte font-bold">
          {error}
        </p>
      )}
      <Button size="lg" fullWidth disabled={busy} onClick={() => void save()}>
        <FloppyDisk aria-hidden size={24} weight="bold" />
        {t("save")}
      </Button>

      <section aria-labelledby="closures-title" className="flex flex-col gap-3">
        <h2 id="closures-title" className="text-title flex items-center gap-2 font-bold">
          <CalendarX aria-hidden size={26} className="text-hibiscus" />
          {t("closures")}
        </h2>
        <p className="text-prune-doux">{t("closuresHelp")}</p>
        {pro.closures.length > 0 && (
          <ul className="flex flex-col gap-2">
            {pro.closures.map((item) => (
              <li
                key={item.id}
                className="border-trait rounded-card flex items-center gap-3 border p-3"
              >
                <span className="flex-1">
                  {t("range", {
                    from: new Date(`${item.starts_on}T12:00:00`),
                    to: new Date(`${item.ends_on}T12:00:00`),
                  })}
                  {item.reason ? ` (${item.reason})` : ""}
                </span>
                <Button
                  variant="quiet"
                  onClick={async () => {
                    await deleteClosure(item.id);
                    await refresh();
                  }}
                >
                  <Trash aria-hidden size={20} />
                  {t("removeClosure")}
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Input
            type="date"
            label={t("startsOn")}
            value={closure.starts_on}
            onChange={(event) => setClosure({ ...closure, starts_on: event.target.value })}
          />
          <Input
            type="date"
            label={t("endsOn")}
            value={closure.ends_on}
            min={closure.starts_on}
            onChange={(event) => setClosure({ ...closure, ends_on: event.target.value })}
          />
        </div>
        <Input
          label={t("reason")}
          value={closure.reason}
          maxLength={120}
          onChange={(event) => setClosure({ ...closure, reason: event.target.value })}
        />
        <Button variant="secondary" disabled={!closure.starts_on} onClick={() => void addOne()}>
          <Plus aria-hidden size={20} weight="bold" />
          {t("addClosure")}
        </Button>
      </section>
    </SectionFrame>
  );
}
