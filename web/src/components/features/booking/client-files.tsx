"use client";

import { ArrowLeft, MagnifyingGlass, UserCircle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getClientRecord, getClientRecords, updateClientRecord } from "@/lib/api/booking";
import { dayName, localDay, timeAt } from "@/lib/booking/time";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

/** Her clients: notes, preferences, history and result photos. Private to the salon. */
export function ClientFilesScreen({ initialId }: { initialId?: string }) {
  const t = useTranslations("booking.clients");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(initialId ?? null);
  useEffect(() => {
    const timer = window.setTimeout(() => setQ(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);
  const query = useQuery({
    queryKey: ["client-records", q],
    queryFn: () => getClientRecords(q || undefined),
  });
  const rows = query.data ?? [];

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
      <p className="text-prune-doux">{t("help")}</p>
      <Input
        label={t("search")}
        leading={<MagnifyingGlass aria-hidden size={22} />}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<UserCircle size={44} weight="duotone" />}
          title={q ? t("noMatch") : t("empty")}
          description={q ? undefined : t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((record) => (
            <li key={record.id}>
              <button
                type="button"
                onClick={() => setOpen(record.id)}
                className="border-trait hover:bg-poudre rounded-card flex min-h-16 w-full flex-col justify-center border p-3 text-left"
              >
                <span className="font-bold">{record.name}</span>
                <span className="text-small text-prune-doux">{record.notes || record.phone}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && <RecordSheet id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function RecordSheet({ id, onClose }: { id: string; onClose: () => void }) {
  const t = useTranslations("booking.clients");
  const tStatus = useTranslations("booking.status");
  const tFlow = useTranslations("booking.flow");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["client-record", id], queryFn: () => getClientRecord(id) });
  const [notes, setNotes] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const record = query.data;

  const save = async () => {
    if (!record) return;
    setBusy(true);
    try {
      await updateClientRecord(id, {
        notes: notes ?? record.notes,
        preferences: preferences ?? record.preferences,
      });
      toast(t("saved"), "success");
      await queryClient.invalidateQueries({ queryKey: ["client-records"] });
      await queryClient.invalidateQueries({ queryKey: ["client-record", id] });
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet
      open
      onOpenChange={(value) => !value && onClose()}
      title={record?.name ?? t("loading")}
      description={record?.phone}
    >
      {!record ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : (
        <div className="flex flex-col gap-4">
          <label className="flex flex-col gap-2 font-bold">
            {t("notes")}
            <textarea
              rows={4}
              maxLength={2000}
              value={notes ?? record.notes}
              onChange={(e) => setNotes(e.target.value)}
              className="border-trait bg-carte rounded-[14px] border-2 p-3 font-normal"
            />
            <span className="text-small text-prune-doux font-normal">{t("notesHelp")}</span>
          </label>
          <Input
            label={t("preferences")}
            hint={t("preferencesHelp")}
            value={preferences ?? record.preferences}
            maxLength={1000}
            onChange={(e) => setPreferences(e.target.value)}
          />
          <Button size="lg" fullWidth disabled={busy} onClick={() => void save()}>
            {t("save")}
          </Button>
          <h3 className="text-lead font-bold">{t("history")}</h3>
          <ul className="flex flex-col gap-2">
            {record.history.map((a) => (
              <li key={a.id} className="border-trait flex flex-col gap-1 rounded-2xl border p-3">
                <span className="font-bold">{a.service_name}</span>
                <span className="text-small">
                  {tFlow("when", {
                    day: dayName(localDay(a.starts_at, a.pro.timezone), locale),
                    time: timeAt(a.starts_at, a.pro.timezone, locale),
                  })}
                </span>
                <span className="text-small text-prune-doux">{tStatus(a.status)}</span>
                {a.photos.length > 0 && (
                  <span className="mt-1 flex gap-2">
                    {a.photos.map((photo, i) => (
                      // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                      <img
                        key={i}
                        src={mediaSrc(photo, "thumb")}
                        alt={t("photo")}
                        className="size-16 rounded-xl object-cover"
                      />
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Sheet>
  );
}
