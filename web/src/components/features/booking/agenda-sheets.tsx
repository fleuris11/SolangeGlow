"use client";

import {
  CalendarX,
  Check,
  CheckCircle,
  Clock,
  Phone,
  ShoppingBag,
  UserCircle,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  addTimeOff,
  adviseProduct,
  cancelByPro,
  completeAppointment,
  confirmAppointment,
  declineAppointment,
  getAgendaAppointment,
  markNoShow,
  moveAppointment,
  proposeTime,
  quickBook,
  type Agenda,
} from "@/lib/api/booking";
import { getMyProducts } from "@/lib/api/shop";
import { dayName, localDay, minutesOfDay, timeAt, zonedToIso } from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

function toInput(minutes: number) {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function fromInput(value: string) {
  const [h, m] = value.split(":").map(Number) as [number, number];
  return h * 60 + m;
}

/** A day and a time, read in the salon's zone. */
function WhenFields({
  day,
  time,
  onDay,
  onTime,
}: {
  day: string;
  time: string;
  onDay: (value: string) => void;
  onTime: (value: string) => void;
}) {
  const t = useTranslations("booking.agenda");
  return (
    <div className="grid grid-cols-2 gap-3">
      <Input label={t("date")} type="date" value={day} onChange={(e) => onDay(e.target.value)} />
      <Input
        label={t("hour")}
        type="time"
        step={300}
        value={time}
        onChange={(e) => onTime(e.target.value)}
      />
    </div>
  );
}

type Mode = "view" | "propose" | "decline" | "move" | "advice";

/** One appointment of the agenda: who, what, and the next step in one tap. */
export function AppointmentSheet({
  id,
  zone,
  canManage,
  onClose,
}: {
  id: string;
  zone: string;
  canManage: boolean;
  onClose: () => void;
}) {
  const t = useTranslations("booking.agenda");
  const tFlow = useTranslations("booking.flow");
  const tStatus = useTranslations("booking.status");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["agenda-appointment", id],
    queryFn: () => getAgendaAppointment(id),
  });
  const [mode, setMode] = useState<Mode>("view");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [day, setDay] = useState("");
  const [time, setTime] = useState("");
  const [productId, setProductId] = useState("");
  const [openedAt] = useState(() => Date.now());
  const products = useQuery({
    queryKey: ["my-products"],
    queryFn: getMyProducts,
    enabled: mode === "advice",
  });

  const detail = query.data;
  const a = detail?.appointment;
  const title = a ? a.client_name : t("loading");
  const when = a
    ? tFlow("when", {
        day: dayName(localDay(a.starts_at, zone), locale),
        time: timeAt(a.starts_at, zone, locale),
      })
    : "";

  const run = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    try {
      await action();
      toast(done, "success");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["agenda"] }),
        queryClient.invalidateQueries({ queryKey: ["agenda-appointment", id] }),
      ]);
      setMode("view");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  const pickTime = (next: Mode) => {
    if (a) {
      setDay(localDay(a.starts_at, zone));
      setTime(toInput(minutesOfDay(a.starts_at, zone)));
    }
    setMode(next);
  };

  const started = a ? new Date(a.starts_at).getTime() <= openedAt : false;
  const productList = products.data
    ? Array.isArray(products.data)
      ? products.data
      : ((products.data as { results?: typeof products.data }).results ?? [])
    : [];

  return (
    <Sheet
      open
      onOpenChange={(value) => !value && onClose()}
      title={title}
      description={a ? `${a.service_name}, ${when}` : undefined}
    >
      {!a || !detail ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : (
        <div className="flex flex-col gap-4">
          <p
            className={cn(
              "flex items-center gap-2 font-bold",
              a.status === "confirmed" && "text-feuille",
            )}
          >
            {a.status === "confirmed" ? (
              <CheckCircle aria-hidden size={24} weight="fill" />
            ) : (
              <Clock aria-hidden size={24} />
            )}
            {tStatus(a.status)}
          </p>
          {detail.no_shows > 0 && (
            <p className="text-alerte flex items-center gap-2 font-bold">
              <WarningCircle aria-hidden size={24} weight="fill" />
              {t("noShows", { count: detail.no_shows })}
            </p>
          )}
          <dl className="flex flex-col gap-2">
            {a.client_phone && (
              <div className="flex items-center gap-2">
                <dt className="sr-only">{t("phone")}</dt>
                <Phone aria-hidden size={22} />
                <dd>
                  <a href={`tel:${a.client_phone}`} className="font-bold underline">
                    {a.client_phone}
                  </a>
                </dd>
              </div>
            )}
            {a.option_names.length > 0 && (
              <div>
                <dt className="text-small text-prune-doux">{t("options")}</dt>
                <dd>{a.option_names.join(", ")}</dd>
              </div>
            )}
            {a.note && (
              <div>
                <dt className="text-small text-prune-doux">{t("note")}</dt>
                <dd>« {a.note} »</dd>
              </div>
            )}
            {a.price_minor !== null && (
              <div>
                <dt className="text-small text-prune-doux">{t("price")}</dt>
                <dd className="font-bold">
                  {formatMoney(a.price_minor, a.currency, locale)}
                  {a.deposit_minor > 0 &&
                    ` ${t("depositPaid", { amount: formatMoney(a.deposit_minor, a.currency, locale) })}`}
                </dd>
              </div>
            )}
            {detail.record && (detail.record.notes || detail.record.preferences) && (
              <div className="bg-poudre rounded-2xl p-3">
                <dt className="text-small text-prune-doux">{t("file")}</dt>
                <dd>
                  {[detail.record.notes, detail.record.preferences].filter(Boolean).join(" — ")}
                </dd>
              </div>
            )}
          </dl>
          {canManage && detail.record && (
            <Link
              href={`/pro/agenda/clients?id=${detail.record.id}`}
              className="flex min-h-12 items-center gap-2 font-bold underline"
            >
              <UserCircle aria-hidden size={24} />
              {t("openFile")}
            </Link>
          )}

          {mode === "view" && (
            <div className="flex flex-col gap-2">
              {a.status === "pending" && (
                <>
                  <Button
                    size="lg"
                    fullWidth
                    disabled={busy}
                    onClick={() => void run(() => confirmAppointment(id), t("confirmed"))}
                  >
                    <Check aria-hidden size={26} weight="bold" />
                    {t("confirm")}
                  </Button>
                  <Button variant="secondary" fullWidth onClick={() => pickTime("propose")}>
                    <Clock aria-hidden size={24} />
                    {t("propose")}
                  </Button>
                  <Button variant="quiet" fullWidth onClick={() => setMode("decline")}>
                    <X aria-hidden size={24} />
                    {t("decline")}
                  </Button>
                </>
              )}
              {a.status === "confirmed" && (
                <>
                  {started && (
                    <Button
                      size="lg"
                      fullWidth
                      disabled={busy}
                      onClick={() => void run(() => completeAppointment(id), t("completed"))}
                    >
                      <CheckCircle aria-hidden size={26} weight="bold" />
                      {t("complete")}
                    </Button>
                  )}
                  <Button variant="secondary" fullWidth onClick={() => pickTime("move")}>
                    <Clock aria-hidden size={24} />
                    {t("move")}
                  </Button>
                  {started && (
                    <Button
                      variant="secondary"
                      fullWidth
                      disabled={busy}
                      onClick={() => void run(() => markNoShow(id), t("noShowDone"))}
                    >
                      <WarningCircle aria-hidden size={24} />
                      {t("noShow")}
                    </Button>
                  )}
                </>
              )}
              {a.status === "completed" && canManage && (
                <Button variant="secondary" fullWidth onClick={() => setMode("advice")}>
                  <ShoppingBag aria-hidden size={24} />
                  {t("advise")}
                </Button>
              )}
              {a.can_cancel && a.status !== "pending" && (
                <Button
                  variant="quiet"
                  fullWidth
                  disabled={busy}
                  onClick={() => void run(() => cancelByPro(id), t("cancelled"))}
                >
                  <CalendarX aria-hidden size={24} />
                  {t("cancel")}
                </Button>
              )}
              {a.can_cancel && <p className="text-small text-prune-doux">{t("cancelHelp")}</p>}
            </div>
          )}

          {(mode === "propose" || mode === "move") && (
            <div className="flex flex-col gap-3">
              <WhenFields day={day} time={time} onDay={setDay} onTime={setTime} />
              {mode === "propose" && (
                <Input
                  label={t("message")}
                  value={message}
                  maxLength={500}
                  onChange={(e) => setMessage(e.target.value)}
                />
              )}
              <Button
                size="lg"
                fullWidth
                disabled={busy || !day || !time}
                onClick={() => {
                  const start = zonedToIso(day, fromInput(time), zone);
                  void run(
                    () =>
                      mode === "move"
                        ? moveAppointment(id, start)
                        : proposeTime(id, start, message),
                    mode === "move" ? t("movedDone") : t("proposed"),
                  );
                }}
              >
                {mode === "move" ? t("moveCta") : t("proposeCta")}
              </Button>
              <Button variant="quiet" fullWidth onClick={() => setMode("view")}>
                {t("back")}
              </Button>
            </div>
          )}

          {mode === "decline" && (
            <div className="flex flex-col gap-3">
              <Input
                label={t("message")}
                hint={t("declineHint")}
                value={message}
                maxLength={500}
                onChange={(e) => setMessage(e.target.value)}
              />
              <Button
                size="lg"
                fullWidth
                disabled={busy}
                onClick={() => void run(() => declineAppointment(id, message), t("declined"))}
              >
                {t("declineCta")}
              </Button>
              <Button variant="quiet" fullWidth onClick={() => setMode("view")}>
                {t("back")}
              </Button>
            </div>
          )}

          {mode === "advice" && (
            <div className="flex flex-col gap-3">
              {products.isPending ? (
                <Skeleton className="h-20 rounded-2xl" />
              ) : productList.length === 0 ? (
                <p className="text-prune-doux">{t("noProduct")}</p>
              ) : (
                <label className="flex flex-col gap-2 font-bold">
                  {t("product")}
                  <select
                    value={productId}
                    onChange={(e) => setProductId(e.target.value)}
                    className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
                  >
                    <option value="">{t("chooseProduct")}</option>
                    {productList
                      .filter((p) => p.status === "published")
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.title}
                        </option>
                      ))}
                  </select>
                </label>
              )}
              <Input
                label={t("adviceNote")}
                value={message}
                maxLength={300}
                onChange={(e) => setMessage(e.target.value)}
              />
              <Button
                size="lg"
                fullWidth
                disabled={busy || !productId}
                onClick={() => void run(() => adviseProduct(id, productId, message), t("advised"))}
              >
                {t("adviseCta")}
              </Button>
              <Button variant="quiet" fullWidth onClick={() => setMode("view")}>
                {t("back")}
              </Button>
            </div>
          )}
        </div>
      )}
    </Sheet>
  );
}

/** A tap on an empty time: a client on the phone, or a blocked range. */
export function QuickSheet({
  agenda,
  zone,
  slot,
  onClose,
}: {
  agenda: Agenda;
  zone: string;
  slot: { day: string; minutes: number; staffId: string };
  onClose: () => void;
}) {
  const t = useTranslations("booking.agenda");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<"book" | "block">("book");
  const [day, setDay] = useState(slot.day);
  const [time, setTime] = useState(toInput(slot.minutes));
  const [until, setUntil] = useState(toInput(Math.min(slot.minutes + 60, 23 * 60 + 55)));
  const [serviceId, setServiceId] = useState(agenda.services[0]?.id ?? "");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const staffId = slot.staffId || agenda.staff[0]?.id;

  const save = async () => {
    setBusy(true);
    try {
      if (kind === "book") {
        await quickBook({
          service_id: serviceId,
          start: zonedToIso(day, fromInput(time), zone),
          staff_id: staffId,
          client_name: name,
          client_phone: phone,
          note,
        });
        toast(t("added"), "success");
      } else {
        await addTimeOff({
          staff_id: staffId,
          kind: "block",
          starts_at: zonedToIso(day, fromInput(time), zone),
          ends_at: zonedToIso(day, fromInput(until), zone),
          note,
        });
        toast(t("blocked"), "success");
      }
      await queryClient.invalidateQueries({ queryKey: ["agenda"] });
      onClose();
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  const who = agenda.staff.find((s) => s.id === staffId)?.name ?? "";
  return (
    <Sheet
      open
      onOpenChange={(value) => !value && onClose()}
      title={t("quickTitle")}
      description={who}
    >
      <div className="flex flex-col gap-4">
        <div
          role="tablist"
          aria-label={t("quickTitle")}
          className="bg-poudre grid grid-cols-2 rounded-full p-1"
        >
          {(["book", "block"] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={kind === key}
              onClick={() => setKind(key)}
              className={cn(
                "min-h-12 rounded-full font-bold",
                kind === key ? "bg-carte text-prune" : "text-prune-doux",
              )}
            >
              {key === "book" ? t("quickBook") : t("quickBlock")}
            </button>
          ))}
        </div>
        <WhenFields day={day} time={time} onDay={setDay} onTime={setTime} />
        {kind === "book" ? (
          <>
            <label className="flex flex-col gap-2 font-bold">
              {t("service")}
              <select
                value={serviceId}
                onChange={(e) => setServiceId(e.target.value)}
                className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
              >
                {agenda.services.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                    {s.price_minor !== null
                      ? ` (${formatMoney(s.price_minor, s.currency, locale)})`
                      : ""}
                  </option>
                ))}
              </select>
            </label>
            <Input label={t("clientName")} value={name} onChange={(e) => setName(e.target.value)} />
            <Input
              label={t("clientPhone")}
              inputMode="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </>
        ) : (
          <Input
            label={t("until")}
            type="time"
            step={300}
            value={until}
            onChange={(e) => setUntil(e.target.value)}
          />
        )}
        <Input
          label={kind === "book" ? t("note") : t("reason")}
          value={note}
          maxLength={120}
          onChange={(e) => setNote(e.target.value)}
        />
        <Button
          size="lg"
          fullWidth
          disabled={
            busy ||
            !day ||
            !time ||
            (kind === "book" && (!serviceId || !name.trim() || phone.trim().length < 8))
          }
          onClick={() => void save()}
        >
          {kind === "book"
            ? t("quickBookCta", {
                time: timeAt(zonedToIso(day, fromInput(time), zone), zone, locale),
              })
            : t("quickBlockCta")}
        </Button>
      </div>
    </Sheet>
  );
}
