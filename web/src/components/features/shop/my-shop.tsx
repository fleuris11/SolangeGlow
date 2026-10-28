"use client";

import {
  Broadcast,
  ChartBar,
  Eye,
  Moped,
  Package,
  Pause,
  PencilSimple,
  Plus,
  Receipt,
  SealWarning,
  Storefront,
  Tag,
  Trash,
  Truck,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  addZone,
  createBundle,
  createFlashSale,
  createPromo,
  deleteBundle,
  deletePromo,
  deleteZone,
  endFlashSale,
  getMyProducts,
  getMyShop,
  getPromotions,
  getShopStats,
  pauseProduct,
  publishProduct,
  setStock,
  updateMyShop,
  type MyProduct,
  type MyShop,
} from "@/lib/api/shop";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney, parseMoney } from "@/lib/money";

import { MySaleLivesTab } from "../live/my-sale-lives";
import { OrderList } from "./orders";

const TABS = ["products", "orders", "lives", "promotions", "delivery", "stats"] as const;
type Tab = (typeof TABS)[number];

function useRun() {
  const toast = useToast();
  const t = useTranslations("shop.my");
  const [busy, setBusy] = useState(false);
  const run = async (step: () => Promise<unknown>, done?: string) => {
    setBusy(true);
    try {
      await step();
      if (done) toast(done, "success");
      return true;
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, run };
}

const STATUS_TONE: Record<string, string> = {
  published: "border-2 border-feuille text-feuille",
  in_review: "bg-or text-sur-or",
  blocked: "border-2 border-alerte text-alerte",
};

function StockField({
  variantId,
  label,
  stock,
}: {
  variantId: string;
  label: string;
  stock: number;
}) {
  const t = useTranslations("shop.my.products");
  const { busy, run } = useRun();
  const [value, setValue] = useState(String(stock));
  const changed = value !== String(stock) && /^\d+$/.test(value);
  return (
    <form
      className="flex items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        void run(() => setStock(variantId, Number(value)), t("stockSaved"));
      }}
    >
      <Input
        label={label || t("stock")}
        inputMode="numeric"
        value={value}
        onChange={(event) => setValue(event.target.value.replace(/\D/g, ""))}
        className="w-28"
      />
      {changed && (
        <Button type="submit" variant="secondary" disabled={busy}>
          {t("save")}
        </Button>
      )}
    </form>
  );
}

function ProductRow({ product, onChange }: { product: MyProduct; onChange: () => void }) {
  const t = useTranslations("shop.my.products");
  const tStatus = useTranslations("shop.productStatus");
  const locale = useLocale();
  const { busy, run } = useRun();
  return (
    <li className="border-trait rounded-card flex flex-col gap-3 border p-4">
      <div className="flex gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
        <img
          src={mediaSrc(product.photo, "thumb")}
          alt=""
          className="bg-poudre size-16 shrink-0 rounded-xl object-cover"
        />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="font-bold">{product.title}</p>
          <p>{formatMoney(product.price_minor, product.currency, locale)}</p>
          <span
            className={cn(
              "text-small self-start rounded-full px-3 py-1 font-bold",
              STATUS_TONE[product.status] ?? "bg-poudre",
            )}
          >
            {tStatus(product.status)}
          </span>
        </div>
      </div>
      {product.review_reason && (
        <p className="text-small bg-poudre rounded-2xl p-3">{product.review_reason}</p>
      )}
      <div className="flex flex-wrap gap-3">
        {product.variants.map((variant) => (
          <StockField
            key={variant.id}
            variantId={variant.id}
            label={variant.label}
            stock={variant.stock}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <Link
          href={`/pro/shop/product/${product.id}`}
          className={buttonClasses({ variant: "secondary" })}
        >
          <PencilSimple aria-hidden size={20} weight="bold" />
          {t("edit")}
        </Link>
        {(product.status === "draft" || product.status === "paused") && (
          <Button
            disabled={busy}
            onClick={() =>
              void run(() => publishProduct(product.id), t("published")).then(onChange)
            }
          >
            <Eye aria-hidden size={20} weight="bold" />
            {t("publish")}
          </Button>
        )}
        {product.status === "published" && (
          <Button
            variant="quiet"
            disabled={busy}
            onClick={() => void run(() => pauseProduct(product.id), t("paused")).then(onChange)}
          >
            <Pause aria-hidden size={20} weight="bold" />
            {t("pause")}
          </Button>
        )}
      </div>
    </li>
  );
}

function ProductsTab() {
  const t = useTranslations("shop.my.products");
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["my-products"], queryFn: getMyProducts });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["my-products"] });
  return (
    <div className="flex flex-col gap-4">
      <Link href="/pro/shop/product/new" className={buttonClasses({ size: "lg", fullWidth: true })}>
        <Plus aria-hidden size={24} weight="bold" />
        {t("add")}
      </Link>
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : (query.data ?? []).length === 0 ? (
        <EmptyState
          icon={<Package size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {(query.data ?? []).map((product) => (
            <ProductRow key={product.id} product={product} onChange={refresh} />
          ))}
        </ul>
      )}
    </div>
  );
}

function PromotionsTab({ shop }: { shop: MyShop }) {
  const t = useTranslations("shop.my.promotions");
  const locale = useLocale();
  const currency = shop.currency;
  const queryClient = useQueryClient();
  const { busy, run } = useRun();
  const query = useQuery({ queryKey: ["my-promotions"], queryFn: getPromotions });
  const products = useQuery({ queryKey: ["my-products"], queryFn: getMyProducts });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["my-promotions"] });
  const [code, setCode] = useState("");
  const [kind, setKind] = useState<"percent" | "amount">("percent");
  const [value, setValue] = useState("");
  const [minimum, setMinimum] = useState("");
  const [saleProduct, setSaleProduct] = useState("");
  const [salePercent, setSalePercent] = useState("20");
  const [saleHours, setSaleHours] = useState("24");
  const [bundleTitle, setBundleTitle] = useState("");
  const [bundlePrice, setBundlePrice] = useState("");
  const [bundleItems, setBundleItems] = useState<string[]>([]);
  const online = (products.data ?? []).filter((p) => p.status === "published");
  const money = (minor: number) => formatMoney(minor, currency, locale);

  if (query.isPending) return <Skeleton className="h-40 rounded-2xl" />;
  const data = query.data;

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="promos" className="flex flex-col gap-3">
        <h2 id="promos" className="text-title font-bold">
          {t("codes")}
        </h2>
        <ul className="flex flex-col gap-2">
          {(data?.promos ?? []).map((promo) => (
            <li
              key={promo.id}
              className="border-trait flex items-center gap-3 rounded-2xl border p-3"
            >
              <span className="flex flex-1 flex-col">
                <span className="font-bold">{promo.code}</span>
                <span className="text-small text-prune-doux">
                  {promo.percent_off !== null
                    ? t("percent", { percent: promo.percent_off })
                    : t("amount", { amount: money(promo.amount_off_minor ?? 0) })}{" "}
                  {t("uses", { count: promo.uses })}
                </span>
              </span>
              <Button
                variant="quiet"
                disabled={busy}
                aria-label={t("delete", { code: promo.code })}
                onClick={() => void run(() => deletePromo(promo.id), t("deleted")).then(refresh)}
              >
                <Trash aria-hidden size={20} />
                {t("deleteShort")}
              </Button>
            </li>
          ))}
        </ul>
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            const amount = kind === "amount" ? parseMoney(value, currency) : null;
            void run(
              () =>
                createPromo({
                  code,
                  percent_off: kind === "percent" ? Number(value) : null,
                  amount_off_minor: amount,
                  min_order_minor: parseMoney(minimum || "0", currency) ?? 0,
                  max_per_client: 1,
                  is_active: true,
                }),
              t("created"),
            ).then((ok) => {
              if (!ok) return;
              setCode("");
              setValue("");
              refresh();
            });
          }}
        >
          <Input
            label={t("code")}
            value={code}
            maxLength={20}
            required
            onChange={(e) => setCode(e.target.value.toUpperCase())}
          />
          <fieldset className="flex gap-2">
            <legend className="mb-2 font-bold">{t("kind")}</legend>
            {(["percent", "amount"] as const).map((option) => (
              <label
                key={option}
                className={cn(
                  "flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold",
                  kind === option ? "border-hibiscus bg-poudre" : "border-trait",
                )}
              >
                <input
                  type="radio"
                  name="promo-kind"
                  className="sr-only"
                  checked={kind === option}
                  onChange={() => setKind(option)}
                />
                {t(option === "percent" ? "kindPercent" : "kindAmount")}
              </label>
            ))}
          </fieldset>
          <Input
            label={kind === "percent" ? t("valuePercent") : t("valueAmount", { currency })}
            inputMode="decimal"
            required
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <Input
            label={t("minimum", { currency })}
            inputMode="decimal"
            value={minimum}
            onChange={(e) => setMinimum(e.target.value)}
          />
          <Button type="submit" variant="secondary" disabled={busy}>
            <Tag aria-hidden size={20} weight="bold" />
            {t("create")}
          </Button>
        </form>
      </section>

      <section aria-labelledby="flash" className="flex flex-col gap-3">
        <h2 id="flash" className="text-title font-bold">
          {t("flash")}
        </h2>
        <ul className="flex flex-col gap-2">
          {(data?.flash_sales ?? []).map((sale) => (
            <li
              key={sale.id}
              className="border-trait flex items-center gap-3 rounded-2xl border p-3"
            >
              <span className="flex flex-1 flex-col">
                <span className="font-bold">{sale.product_title}</span>
                <span className="text-small text-prune-doux">
                  {t("flashLine", {
                    percent: sale.percent_off,
                    end: new Intl.DateTimeFormat(locale, {
                      dateStyle: "short",
                      timeStyle: "short",
                    }).format(new Date(sale.ends_at)),
                  })}
                </span>
              </span>
              <Button
                variant="quiet"
                disabled={busy}
                onClick={() => void run(() => endFlashSale(sale.id), t("ended")).then(refresh)}
              >
                {t("end")}
              </Button>
            </li>
          ))}
        </ul>
        {online.length > 0 && (
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              const start = new Date();
              const end = new Date(start.getTime() + Number(saleHours) * 3_600_000);
              void run(
                () =>
                  createFlashSale({
                    product_id: saleProduct || (online[0]?.id ?? ""),
                    percent_off: Number(salePercent),
                    starts_at: start.toISOString(),
                    ends_at: end.toISOString(),
                  }),
                t("flashCreated"),
              ).then(refresh);
            }}
          >
            <label className="flex flex-col gap-2 font-bold">
              {t("product")}
              <select
                value={saleProduct || (online[0]?.id ?? "")}
                onChange={(e) => setSaleProduct(e.target.value)}
                className="rounded-field bg-poudre min-h-12 px-3"
              >
                {online.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.title}
                  </option>
                ))}
              </select>
            </label>
            <Input
              label={t("valuePercent")}
              inputMode="numeric"
              value={salePercent}
              onChange={(e) => setSalePercent(e.target.value.replace(/\D/g, ""))}
            />
            <label className="flex flex-col gap-2 font-bold">
              {t("duration")}
              <select
                value={saleHours}
                onChange={(e) => setSaleHours(e.target.value)}
                className="rounded-field bg-poudre min-h-12 px-3"
              >
                {["6", "12", "24", "48", "72"].map((hours) => (
                  <option key={hours} value={hours}>
                    {t("hours", { count: Number(hours) })}
                  </option>
                ))}
              </select>
            </label>
            <Button type="submit" variant="secondary" disabled={busy}>
              {t("startFlash")}
            </Button>
          </form>
        )}
      </section>

      <section aria-labelledby="bundles" className="flex flex-col gap-3">
        <h2 id="bundles" className="text-title font-bold">
          {t("bundles")}
        </h2>
        <ul className="flex flex-col gap-2">
          {(data?.bundles ?? []).map((bundle) => (
            <li
              key={bundle.id}
              className="border-trait flex items-center gap-3 rounded-2xl border p-3"
            >
              <span className="flex flex-1 flex-col">
                <span className="font-bold">{bundle.title}</span>
                <span className="text-small text-prune-doux">
                  {money(bundle.price_minor)} {t("instead", { amount: money(bundle.worth_minor) })}
                </span>
              </span>
              <Button
                variant="quiet"
                disabled={busy}
                aria-label={t("delete", { code: bundle.title })}
                onClick={() => void run(() => deleteBundle(bundle.id), t("deleted")).then(refresh)}
              >
                <Trash aria-hidden size={20} />
                {t("deleteShort")}
              </Button>
            </li>
          ))}
        </ul>
        {online.length > 1 && (
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              const price = parseMoney(bundlePrice, currency);
              void run(
                () =>
                  createBundle({
                    title: bundleTitle,
                    price_minor: price ?? 0,
                    items: bundleItems.map((variant_id) => ({ variant_id, quantity: 1 })),
                    is_active: true,
                  }),
                t("bundleCreated"),
              ).then((ok) => {
                if (!ok) return;
                setBundleTitle("");
                setBundlePrice("");
                setBundleItems([]);
                refresh();
              });
            }}
          >
            <Input
              label={t("bundleTitle")}
              required
              value={bundleTitle}
              onChange={(e) => setBundleTitle(e.target.value)}
            />
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-2 font-bold">{t("bundleItems")}</legend>
              {online.flatMap((product) =>
                product.variants.map((variant) => (
                  <label key={variant.id} className="flex min-h-12 items-center gap-3">
                    <input
                      type="checkbox"
                      className="accent-hibiscus size-6"
                      checked={bundleItems.includes(variant.id)}
                      onChange={(e) =>
                        setBundleItems(
                          e.target.checked
                            ? [...bundleItems, variant.id]
                            : bundleItems.filter((id) => id !== variant.id),
                        )
                      }
                    />
                    {[product.title, variant.label].filter(Boolean).join(" ")}
                  </label>
                )),
              )}
            </fieldset>
            <Input
              label={t("bundlePrice", { currency })}
              inputMode="decimal"
              required
              value={bundlePrice}
              onChange={(e) => setBundlePrice(e.target.value)}
            />
            <Button type="submit" variant="secondary" disabled={busy || bundleItems.length < 2}>
              {t("createBundle")}
            </Button>
          </form>
        )}
      </section>
    </div>
  );
}

function DeliveryTab({ shop, onChange }: { shop: MyShop; onChange: (shop: MyShop) => void }) {
  const t = useTranslations("shop.my.delivery");
  const locale = useLocale();
  const { busy, run } = useRun();
  const delivery = shop.delivery;
  const [form, setForm] = useState({
    pickup_note: delivery.pickup_note,
    partner_name: delivery.partner_name,
    return_policy: delivery.return_policy,
  });
  const [mode, setMode] = useState<"seller" | "partner">("seller");
  const [zoneName, setZoneName] = useState("");
  const [fee, setFee] = useState("");
  const save = (changes: Parameters<typeof updateMyShop>[0], done?: string) =>
    run(async () => onChange(await updateMyShop(changes)), done);

  const icon = (node: ReactNode) => <span className="text-hibiscus">{node}</span>;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <SwitchRow
          icon={icon(<Storefront size={24} weight="duotone" />)}
          label={t("open")}
          description={t("openHelp")}
          checked={delivery.is_open}
          disabled={busy}
          onChange={(value) => void save({ is_open: value })}
        />
        <SwitchRow
          icon={icon(<Storefront size={24} weight="duotone" />)}
          label={t("pickup")}
          description={t("pickupHelp")}
          checked={delivery.pickup}
          disabled={busy}
          onChange={(value) => void save({ pickup: value })}
        />
        <SwitchRow
          icon={icon(<Moped size={24} weight="duotone" />)}
          label={t("seller")}
          description={t("sellerHelp")}
          checked={delivery.seller_delivery}
          disabled={busy}
          onChange={(value) => void save({ seller_delivery: value })}
        />
        <SwitchRow
          icon={icon(<Truck size={24} weight="duotone" />)}
          label={t("partner")}
          description={t("partnerHelp")}
          checked={delivery.partner_delivery}
          disabled={busy}
          onChange={(value) => void save({ partner_delivery: value })}
        />
      </div>
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void save(form, t("saved"));
        }}
      >
        <Input
          label={t("pickupNote")}
          value={form.pickup_note}
          maxLength={300}
          onChange={(e) => setForm({ ...form, pickup_note: e.target.value })}
        />
        <Input
          label={t("partnerName")}
          value={form.partner_name}
          maxLength={80}
          onChange={(e) => setForm({ ...form, partner_name: e.target.value })}
        />
        <Input
          label={t("returns")}
          value={form.return_policy}
          maxLength={1000}
          onChange={(e) => setForm({ ...form, return_policy: e.target.value })}
        />
        <Button type="submit" variant="secondary" disabled={busy}>
          {t("save")}
        </Button>
      </form>
      <section aria-labelledby="zones" className="flex flex-col gap-3">
        <h2 id="zones" className="text-title font-bold">
          {t("zones")}
        </h2>
        <p className="text-small text-prune-doux">{t("zonesHelp")}</p>
        <ul className="flex flex-col gap-2">
          {delivery.zones.map((zone) => (
            <li
              key={zone.id}
              className="border-trait flex items-center gap-3 rounded-2xl border p-3"
            >
              <span className="flex flex-1 flex-col">
                <span className="font-bold">{zone.name}</span>
                <span className="text-small text-prune-doux">
                  {t(zone.mode === "seller" ? "bySeller" : "byPartner")}{" "}
                  {formatMoney(zone.fee_minor, shop.currency, locale)}
                </span>
              </span>
              <Button
                variant="quiet"
                disabled={busy}
                aria-label={t("deleteZone", { name: zone.name })}
                onClick={() => void run(async () => onChange(await deleteZone(zone.id)))}
              >
                <Trash aria-hidden size={20} />
                {t("deleteShort")}
              </Button>
            </li>
          ))}
        </ul>
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            const minor = parseMoney(fee || "0", shop.currency);
            void run(async () => {
              onChange(await addZone({ mode, name: zoneName, fee_minor: minor ?? -1 }));
              setZoneName("");
              setFee("");
            }, t("zoneAdded"));
          }}
        >
          <fieldset className="flex flex-wrap gap-2">
            <legend className="mb-2 font-bold">{t("zoneBy")}</legend>
            {(["seller", "partner"] as const).map((option) => (
              <label
                key={option}
                className={cn(
                  "flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold",
                  mode === option ? "border-hibiscus bg-poudre" : "border-trait",
                )}
              >
                <input
                  type="radio"
                  name="zone-mode"
                  className="sr-only"
                  checked={mode === option}
                  onChange={() => setMode(option)}
                />
                {t(option === "seller" ? "bySeller" : "byPartner")}
              </label>
            ))}
          </fieldset>
          <Input
            label={t("zoneName")}
            required
            value={zoneName}
            maxLength={80}
            onChange={(e) => setZoneName(e.target.value)}
          />
          <Input
            label={t("zoneFee", { currency: shop.currency })}
            inputMode="decimal"
            value={fee}
            onChange={(e) => setFee(e.target.value)}
          />
          <Button type="submit" variant="secondary" disabled={busy}>
            <Plus aria-hidden size={20} weight="bold" />
            {t("addZone")}
          </Button>
        </form>
      </section>
    </div>
  );
}

function StatsTab({ currency }: { currency: string }) {
  const t = useTranslations("shop.my.stats");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["my-shop-stats"], queryFn: getShopStats });
  if (query.isPending) return <Skeleton className="h-40 rounded-2xl" />;
  const stats = query.data;
  if (!stats) return null;
  const money = (value: number) => formatMoney(value, stats.currency || currency, locale);
  const cards = [
    [t("orders"), String(stats.orders)],
    [t("sales"), money(stats.sales_minor)],
    [t("completed"), money(stats.completed_minor)],
    [t("toHandle"), String(stats.new + stats.preparing)],
  ];
  return (
    <div className="flex flex-col gap-6">
      <p className="text-prune-doux">{t("period", { days: stats.days })}</p>
      <dl className="grid grid-cols-2 gap-3">
        {cards.map(([label, value]) => (
          <div key={label} className="bg-poudre rounded-card flex flex-col gap-1 p-4">
            <dt className="text-small">{label}</dt>
            <dd className="text-title font-bold">{value}</dd>
          </div>
        ))}
      </dl>
      <section aria-labelledby="top" className="flex flex-col gap-2">
        <h2 id="top" className="text-title font-bold">
          {t("top")}
        </h2>
        {stats.top.length === 0 ? (
          <p className="text-prune-doux">{t("noSales")}</p>
        ) : (
          <ol className="flex flex-col gap-2">
            {stats.top.map((row) => (
              <li key={row.product_id} className="flex justify-between gap-3">
                <span>{t("topLine", { title: row.title, count: row.quantity })}</span>
                <span className="font-bold">{money(row.amount_minor)}</span>
              </li>
            ))}
          </ol>
        )}
      </section>
      <section aria-labelledby="low" className="flex flex-col gap-2">
        <h2 id="low" className="text-title font-bold">
          {t("runningOut")}
        </h2>
        {stats.running_out.length === 0 ? (
          <p className="text-prune-doux">{t("allGood")}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {stats.running_out.map((row) => (
              <li key={row.variant_id} className="flex justify-between gap-3">
                <span>{[row.title, row.label].filter(Boolean).join(" ")}</span>
                <span className="text-alerte font-bold">{t("left", { count: row.stock })}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

const TAB_ICONS: Record<Tab, ReactNode> = {
  products: <Package aria-hidden size={20} weight="bold" />,
  orders: <Receipt aria-hidden size={20} weight="bold" />,
  lives: <Broadcast aria-hidden size={20} weight="bold" />,
  promotions: <Tag aria-hidden size={20} weight="bold" />,
  delivery: <Truck aria-hidden size={20} weight="bold" />,
  stats: <ChartBar aria-hidden size={20} weight="bold" />,
};

/** « My shop »: products and stock, orders, promotions, hand-over, simple numbers. */
export function MyShopScreen() {
  const t = useTranslations("shop.my");
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["my-shop"], queryFn: getMyShop, retry: false });
  const [tab, setTab] = useState<Tab>("products");

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (query.isError || !query.data) {
    return (
      <div className="flex flex-col items-start gap-4">
        <p className="text-lead font-bold">
          {query.error instanceof ApiError ? query.error.message : t("error")}
        </p>
        <Link href="/pro/start" className={buttonClasses({ size: "lg" })}>
          {t("becomePro")}
        </Link>
      </div>
    );
  }
  const shop = query.data;
  const setShop = (value: MyShop) => queryClient.setQueryData(["my-shop"], value);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <h1 className="text-headline font-bold">{t("title")}</h1>
        {shop.shop.slug && (
          <Link
            href={`/${shop.shop.slug}/shop`}
            className="text-hibiscus self-start font-bold underline"
          >
            {t("see")}
          </Link>
        )}
        {!shop.can_sell && (
          <div className="bg-poudre rounded-card flex flex-col items-start gap-2 p-4" role="status">
            <p className="flex items-center gap-2 font-bold">
              <SealWarning aria-hidden size={24} weight="duotone" className="text-alerte" />
              {t("verify")}
            </p>
            <Link href="/pro/verification" className={buttonClasses({ variant: "secondary" })}>
              {t("verifyCta")}
            </Link>
          </div>
        )}
        {!shop.enabled && <p className="bg-poudre rounded-2xl p-3">{t("disabled")}</p>}
      </header>
      <div role="tablist" aria-label={t("tabs")} className="-mx-4 flex gap-2 overflow-x-auto px-4">
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cn(
              "inline-flex min-h-12 shrink-0 items-center gap-2 rounded-full border-2 px-4 font-bold",
              tab === key ? "border-hibiscus bg-hibiscus text-sur-hibiscus" : "border-trait",
            )}
          >
            {TAB_ICONS[key]}
            {t(`tab.${key}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === "products" && <ProductsTab />}
        {tab === "orders" && <OrderList role="seller" showTabs={false} />}
        {tab === "lives" && <MySaleLivesTab />}
        {tab === "promotions" && <PromotionsTab shop={shop} />}
        {tab === "delivery" && <DeliveryTab shop={shop} onChange={setShop} />}
        {tab === "stats" && <StatsTab currency={shop.currency} />}
      </div>
    </div>
  );
}
