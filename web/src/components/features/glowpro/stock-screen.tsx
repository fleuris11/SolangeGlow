"use client";

import { Barcode, Package, Plus, Scissors, Warning } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { getAgenda } from "@/lib/api/booking";
import { ApiError } from "@/lib/api/client";
import {
  addStockItem,
  countStock,
  findByBarcode,
  getConsumption,
  getMovements,
  getStock,
  moveStock,
  setConsumption,
  type StockItem,
} from "@/lib/api/glowpro";
import { cn } from "@/lib/cn";

import { PremiumGate } from "./premium-gate";

// The camera and its reader are downloaded when the scanner opens.
const Scanner = dynamic(() => import("./scanner").then((m) => m.Scanner));

const STOCK_KEY = ["stock"];

function useRun() {
  const t = useTranslations("glowpro.stock");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const run = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    try {
      await action();
      toast(done, "success");
      await queryClient.invalidateQueries({ queryKey: STOCK_KEY });
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

/** « Stock »: what is left, scan a product, deliveries, sales, inventory, alerts. */
export function StockScreen() {
  const t = useTranslations("glowpro.stock");
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <Package aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} />
      </div>
      <PremiumGate feature="stock" title={t("premiumTitle")} text={t("premiumText")}>
        <StockList />
      </PremiumGate>
    </div>
  );
}

function StockList() {
  const t = useTranslations("glowpro.stock");
  const tUnit = useTranslations("glowpro.units");
  const toast = useToast();
  const query = useQuery({ queryKey: STOCK_KEY, queryFn: () => getStock() });
  const [scanning, setScanning] = useState(false);
  const [adding, setAdding] = useState<string | null>(null);
  const [open, setOpen] = useState<StockItem | null>(null);
  const [usage, setUsage] = useState(false);
  const items = query.data ?? [];
  const low = items.filter((i) => i.low);

  const onCode = useCallback(
    async (code: string) => {
      setScanning(false);
      try {
        setOpen(await findByBarcode(code));
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 404) {
          toast(t("unknownCode"), "info");
          setAdding(code);
        } else {
          toast(t("error"), "warning");
        }
      }
    },
    [t, toast],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button size="lg" fullWidth onClick={() => setScanning(true)}>
          <Barcode aria-hidden size={26} weight="bold" />
          {t("scan")}
        </Button>
        <Button size="lg" variant="secondary" fullWidth onClick={() => setAdding("")}>
          <Plus aria-hidden size={24} weight="bold" />
          {t("add")}
        </Button>
      </div>
      <Button variant="quiet" fullWidth onClick={() => setUsage(true)}>
        <Scissors aria-hidden size={22} />
        {t("usage")}
      </Button>
      {low.length > 0 && (
        <p
          role="status"
          className="bg-poudre text-alerte flex items-center gap-2 rounded-2xl p-3 font-bold"
        >
          <Warning aria-hidden size={24} weight="fill" />
          {t("lowCount", { count: low.length })}
        </p>
      )}
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Package size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => setOpen(item)}
                className={cn(
                  "rounded-card flex min-h-16 w-full items-center gap-3 border p-3 text-left",
                  item.low ? "border-alerte bg-poudre" : "border-trait bg-carte",
                )}
              >
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate font-bold">{item.name}</span>
                  <span className="text-small text-prune-doux">
                    {item.kind === "retail" ? t("retail") : t("professional")}
                    {item.ean && `, ${item.ean}`}
                  </span>
                </span>
                <span className={cn("shrink-0 font-bold", item.low && "text-alerte")}>
                  {item.quantity} {tUnit(item.unit)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <Sheet open={scanning} onOpenChange={setScanning} title={t("scanTitle")}>
        {scanning && <Scanner onCode={(code) => void onCode(code)} />}
      </Sheet>
      {adding !== null && <AddSheet ean={adding} onClose={() => setAdding(null)} />}
      {open && <ItemSheet item={open} onClose={() => setOpen(null)} />}
      {usage && <UsageSheet items={items} onClose={() => setUsage(false)} />}
    </div>
  );
}

function AddSheet({ ean, onClose }: { ean: string; onClose: () => void }) {
  const t = useTranslations("glowpro.stock");
  const tUnit = useTranslations("glowpro.units");
  const { busy, run } = useRun();
  const [name, setName] = useState("");
  const [code, setCode] = useState(ean);
  const [kind, setKind] = useState<"retail" | "professional">("professional");
  const [unit, setUnit] = useState<"piece" | "ml" | "g">("piece");
  const [quantity, setQuantity] = useState("");
  const [threshold, setThreshold] = useState("");

  const save = async () => {
    const ok = await run(
      () =>
        addStockItem({
          name,
          kind,
          unit,
          ean: code,
          quantity: Number(quantity) || 0,
          alert_threshold: Number(threshold) || 0,
        }),
      t("added"),
    );
    if (ok) onClose();
  };

  return (
    <Sheet open onOpenChange={(value) => !value && onClose()} title={t("add")}>
      <div className="flex flex-col gap-4">
        <Input
          label={t("name")}
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label={t("barcode")}
          hint={t("barcodeHint")}
          inputMode="numeric"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <fieldset className="flex flex-col gap-2">
          <legend className="font-bold">{t("kind")}</legend>
          {(["professional", "retail"] as const).map((value) => (
            <label key={value} className="flex min-h-12 items-center gap-3">
              <input
                type="radio"
                name="kind"
                className="accent-hibiscus size-6"
                checked={kind === value}
                onChange={() => setKind(value)}
              />
              {value === "retail" ? t("retail") : t("professional")}
            </label>
          ))}
        </fieldset>
        <label className="flex flex-col gap-2 font-bold">
          {t("unit")}
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value as "piece")}
            className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
          >
            {(["piece", "ml", "g"] as const).map((value) => (
              <option key={value} value={value}>
                {tUnit(value)}
              </option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <Input
            label={t("quantity")}
            inputMode="numeric"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value.replace(/\D/g, ""))}
          />
          <Input
            label={t("threshold")}
            inputMode="numeric"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value.replace(/\D/g, ""))}
          />
        </div>
        <Button size="lg" fullWidth disabled={busy || !name.trim()} onClick={() => void save()}>
          {t("save")}
        </Button>
      </div>
    </Sheet>
  );
}

function ItemSheet({ item, onClose }: { item: StockItem; onClose: () => void }) {
  const t = useTranslations("glowpro.stock");
  const tUnit = useTranslations("glowpro.units");
  const tKind = useTranslations("glowpro.movements");
  const { busy, run } = useRun();
  const history = useQuery({
    queryKey: [...STOCK_KEY, item.id],
    queryFn: () => getMovements(item.id),
  });
  const [kind, setKind] = useState<"in" | "out" | "sale" | "loss">("in");
  const [quantity, setQuantity] = useState("");
  const [counted, setCounted] = useState("");
  const locale = useLocale();

  return (
    <Sheet
      open
      onOpenChange={(value) => !value && onClose()}
      title={item.name}
      description={`${item.quantity} ${tUnit(item.unit)}`}
    >
      <div className="flex flex-col gap-5">
        <fieldset className="flex flex-col gap-3">
          <legend className="font-bold">{t("move")}</legend>
          <div className="flex flex-wrap gap-2">
            {(["in", "sale", "out", "loss"] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={kind === value}
                onClick={() => setKind(value)}
                className={cn(
                  "min-h-12 rounded-full border-2 px-4 font-bold",
                  kind === value ? "border-hibiscus bg-hibiscus text-sur-hibiscus" : "border-trait",
                )}
              >
                {tKind(value)}
              </button>
            ))}
          </div>
          <Input
            label={t("howMany", { unit: tUnit(item.unit) })}
            inputMode="numeric"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value.replace(/\D/g, ""))}
          />
          <Button
            fullWidth
            disabled={busy || !Number(quantity)}
            onClick={() =>
              void run(
                () => moveStock(item.id, { kind, quantity: Number(quantity) }),
                t("moved"),
              ).then((ok) => ok && setQuantity(""))
            }
          >
            {t("record")}
          </Button>
        </fieldset>
        <fieldset className="flex flex-col gap-3">
          <legend className="font-bold">{t("inventory")}</legend>
          <Input
            label={t("counted")}
            inputMode="numeric"
            value={counted}
            onChange={(e) => setCounted(e.target.value.replace(/\D/g, ""))}
          />
          <Button
            variant="secondary"
            fullWidth
            disabled={busy || counted === ""}
            onClick={() => void run(() => countStock(item.id, Number(counted)), t("countedDone"))}
          >
            {t("saveCount")}
          </Button>
        </fieldset>
        <section aria-labelledby="history" className="flex flex-col gap-2">
          <h3 id="history" className="font-bold">
            {t("history")}
          </h3>
          <ul className="flex flex-col gap-1">
            {(history.data ?? []).map((m) => (
              <li key={m.id} className="text-small flex justify-between gap-2">
                <span>
                  {new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(
                    new Date(m.created_at),
                  )}{" "}
                  {tKind(m.kind)}
                </span>
                <span className="font-bold">
                  {m.change > 0 ? `+${m.change}` : m.change} → {m.after}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </Sheet>
  );
}

function UsageSheet({ items, onClose }: { items: StockItem[]; onClose: () => void }) {
  const t = useTranslations("glowpro.stock");
  const tUnit = useTranslations("glowpro.units");
  const { busy, run } = useRun();
  const services = useQuery({
    queryKey: ["agenda", "services"],
    queryFn: () => getAgenda({ start: new Date().toISOString().slice(0, 10), days: 1 }),
  });
  const [serviceId, setServiceId] = useState("");
  const [rows, setRows] = useState<Record<string, string>>({});
  const used = items.filter((i) => i.kind === "professional");

  const load = async (id: string) => {
    setServiceId(id);
    const current = await getConsumption(id);
    setRows(Object.fromEntries(current.map((r) => [r.item_id, String(r.quantity)])));
  };

  const save = () =>
    run(
      () =>
        setConsumption(
          serviceId,
          Object.entries(rows)
            .filter(([, q]) => Number(q) > 0)
            .map(([item_id, q]) => ({ item_id, quantity: Number(q) })),
        ),
      t("usageSaved"),
    );

  return (
    <Sheet
      open
      onOpenChange={(value) => !value && onClose()}
      title={t("usage")}
      description={t("usageHelp")}
    >
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-2 font-bold">
          {t("service")}
          <select
            value={serviceId}
            onChange={(e) => void load(e.target.value)}
            className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
          >
            <option value="">{t("chooseService")}</option>
            {(services.data?.services ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        {serviceId &&
          used.map((item) => (
            <Input
              key={item.id}
              label={`${item.name} (${tUnit(item.unit)})`}
              inputMode="numeric"
              value={rows[item.id] ?? ""}
              onChange={(e) => setRows({ ...rows, [item.id]: e.target.value.replace(/\D/g, "") })}
            />
          ))}
        {serviceId && (
          <Button size="lg" fullWidth disabled={busy} onClick={() => void save()}>
            {t("saveUsage")}
          </Button>
        )}
      </div>
    </Sheet>
  );
}
