"use client";

import { Clock, PencilSimple, Plus, Trash, Van } from "@phosphor-icons/react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { PriceTag } from "@/components/ui/price-tag";
import { Sheet } from "@/components/ui/sheet";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  createCategory,
  createService,
  deleteService,
  myProQueryKey,
  updateService,
  type MyPro,
  type Service,
  type ServiceInput,
} from "@/lib/api/pros";
import { currencyExponent } from "@/lib/money";
import { durationParts } from "@/lib/pros/format";

import { fieldClass, SectionFrame } from "./section-frame";

type Draft = {
  name: string;
  description: string;
  categoryId: string;
  newCategory: string;
  priceKind: "fixed" | "from" | "quote";
  price: string;
  work: number;
  pose: number;
  after: number;
  atHome: boolean;
  options: { name: string; price: string }[];
};

const WORK = [15, 30, 45, 60, 75, 90, 120, 150, 180, 240, 300, 360, 480];
const POSE = [0, 10, 15, 20, 30, 40, 45, 60, 90];
const AFTER = [0, 10, 15, 20, 30, 45, 60, 90];

function toMinor(value: string, currency: string): number | null {
  const number = Number.parseFloat(value.replace(/\s/g, "").replace(",", "."));
  if (!Number.isFinite(number) || number < 0) return null;
  return Math.round(number * 10 ** currencyExponent(currency));
}

function toMajor(minor: number | null | undefined, currency: string): string {
  if (minor === null || minor === undefined) return "";
  return String(minor / 10 ** currencyExponent(currency));
}

function draftOf(service: Service | null, currency: string): Draft {
  if (!service) {
    return {
      name: "",
      description: "",
      categoryId: "",
      newCategory: "",
      priceKind: "fixed",
      price: "",
      work: 60,
      pose: 0,
      after: 0,
      atHome: false,
      options: [],
    };
  }
  const waitIndex = service.steps.findIndex((step) => step.kind === "wait");
  const before = waitIndex === -1 ? service.steps : service.steps.slice(0, waitIndex);
  const later = waitIndex === -1 ? [] : service.steps.slice(waitIndex + 1);
  return {
    name: service.name,
    description: service.description,
    categoryId: service.category_id ?? "",
    newCategory: "",
    priceKind: service.price_kind,
    price: toMajor(service.price_minor, currency),
    work: before.reduce((sum, step) => sum + step.duration_minutes, 0),
    pose: service.waiting_minutes,
    after: later.reduce((sum, step) => sum + (step.kind === "work" ? step.duration_minutes : 0), 0),
    atHome: service.available_at_home,
    options: service.options.map((option) => ({
      name: option.name,
      price: toMajor(option.price_minor ?? 0, currency),
    })),
  };
}

/** Price list: each service with its time (and waiting time), price and options. */
export function ServicesSection({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.services");
  const tShowcase = useTranslations("pros.showcase");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Service | "new" | null>(null);
  const [draft, setDraft] = useState<Draft>(draftOf(null, pro.currency));
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const currency = pro.currency || "XOF";
  const set = (changes: Partial<Draft>) => setDraft((current) => ({ ...current, ...changes }));

  const open = (service: Service | null) => {
    setDraft(draftOf(service, currency));
    setError(undefined);
    setEditing(service ?? "new");
  };

  const refresh = () => queryClient.invalidateQueries({ queryKey: myProQueryKey });

  const save = async () => {
    setBusy(true);
    setError(undefined);
    try {
      let categoryId: string | null = draft.categoryId || null;
      if (draft.categoryId === "new" && draft.newCategory.trim()) {
        categoryId = (await createCategory(draft.newCategory.trim())).id;
      } else if (draft.categoryId === "new") categoryId = null;
      const steps: ServiceInput["steps"] = [{ kind: "work", duration_minutes: draft.work }];
      if (draft.pose > 0) {
        steps.push({ kind: "wait", duration_minutes: draft.pose, label: t("poseLabel") });
        if (draft.after > 0) steps.push({ kind: "work", duration_minutes: draft.after });
      }
      const body: ServiceInput = {
        name: draft.name,
        description: draft.description,
        category_id: categoryId,
        price_kind: draft.priceKind,
        price_minor: draft.priceKind === "quote" ? null : toMinor(draft.price, currency),
        available_at_home: draft.atHome,
        steps,
        options: draft.options
          .filter((option) => option.name.trim())
          .map((option) => ({
            name: option.name.trim(),
            price_minor: toMinor(option.price || "0", currency) ?? 0,
          })),
      };
      if (editing === "new") await createService(body);
      else if (editing) await updateService(editing.id, body);
      await refresh();
      setEditing(null);
      toast(t("saved"), "success");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!editing || editing === "new") return;
    setBusy(true);
    try {
      await deleteService(editing.id);
      await refresh();
      setEditing(null);
      toast(t("removed"), "success");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <Button size="lg" fullWidth onClick={() => open(null)}>
        <Plus aria-hidden size={24} weight="bold" />
        {t("add")}
      </Button>

      {pro.services.length === 0 ? (
        <p className="text-prune-doux">{t("empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {pro.services.map((service) => (
            <li
              key={service.id}
              className="border-trait bg-carte rounded-card flex items-center gap-3 border p-4"
            >
              <span className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="font-bold">{service.name}</span>
                <span className="text-small text-prune-doux flex flex-wrap items-center gap-x-3">
                  <span className="inline-flex items-center gap-1">
                    <Clock aria-hidden size={16} />
                    {tShowcase("duration", durationParts(service.duration_minutes))}
                  </span>
                  {service.price_minor === null ? (
                    tShowcase("quote")
                  ) : (
                    <PriceTag
                      amountMinor={service.price_minor}
                      currency={service.currency}
                      prefix={service.price_kind === "from" ? tShowcase("priceFrom") : undefined}
                    />
                  )}
                </span>
              </span>
              <Button variant="secondary" onClick={() => open(service)}>
                <PencilSimple aria-hidden size={20} weight="bold" />
                {t("edit")}
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Sheet
        open={editing !== null}
        onOpenChange={(value) => !value && setEditing(null)}
        title={editing === "new" ? t("newTitle") : t("editTitle")}
      >
        <div className="flex flex-col gap-5">
          <Input
            label={t("name")}
            placeholder={t("namePlaceholder")}
            value={draft.name}
            onChange={(event) => set({ name: event.target.value })}
            maxLength={80}
          />

          <div className="flex flex-col gap-2">
            <label htmlFor="service-category" className="font-bold">
              {t("category")}
            </label>
            <select
              id="service-category"
              value={draft.categoryId}
              onChange={(event) => set({ categoryId: event.target.value })}
              className={fieldClass}
            >
              <option value="">{t("noCategory")}</option>
              {pro.categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
              <option value="new">{t("newCategory")}</option>
            </select>
            {draft.categoryId === "new" && (
              <Input
                label={t("newCategoryName")}
                value={draft.newCategory}
                onChange={(event) => set({ newCategory: event.target.value })}
                maxLength={60}
              />
            )}
          </div>

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("priceKind")}</legend>
            <div className="flex flex-wrap gap-2">
              {(["fixed", "from", "quote"] as const).map((kind) => (
                <Chip
                  key={kind}
                  selected={draft.priceKind === kind}
                  onClick={() => set({ priceKind: kind })}
                >
                  {t(`priceKinds.${kind}`)}
                </Chip>
              ))}
            </div>
          </fieldset>
          {draft.priceKind !== "quote" && (
            <Input
              label={t("price", { currency: currency === "XOF" ? "FCFA" : "€" })}
              inputMode="decimal"
              value={draft.price}
              onChange={(event) => set({ price: event.target.value })}
            />
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {(
              [
                ["work", WORK],
                ["pose", POSE],
                ["after", AFTER],
              ] as const
            ).map(([key, values]) =>
              key === "after" && draft.pose === 0 ? null : (
                <div key={key} className="flex flex-col gap-2">
                  <label htmlFor={`service-${key}`} className="font-bold">
                    {t(`time.${key}`)}
                  </label>
                  <select
                    id={`service-${key}`}
                    value={draft[key]}
                    onChange={(event) => set({ [key]: Number(event.target.value) })}
                    className={fieldClass}
                  >
                    {values.map((minutes) => (
                      <option key={minutes} value={minutes}>
                        {minutes === 0 ? t("none") : tShowcase("duration", durationParts(minutes))}
                      </option>
                    ))}
                  </select>
                </div>
              ),
            )}
          </div>
          <p className="text-small text-prune-doux">{t("poseHelp")}</p>

          <div className="flex flex-col gap-2">
            <label htmlFor="service-description" className="font-bold">
              {t("description")}
            </label>
            <textarea
              id="service-description"
              rows={3}
              maxLength={1000}
              value={draft.description}
              onChange={(event) => set({ description: event.target.value })}
              className={fieldClass}
            />
          </div>

          <SwitchRow
            icon={<Van size={28} weight="duotone" />}
            label={t("atHome")}
            description={t("atHomeText")}
            checked={draft.atHome}
            onChange={(value) => set({ atHome: value })}
          />

          <fieldset className="flex flex-col gap-3">
            <legend className="mb-2 font-bold">{t("options")}</legend>
            <p className="text-small text-prune-doux">{t("optionsHelp")}</p>
            {draft.options.map((option, index) => (
              <div key={index} className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <Input
                  className="flex-1"
                  label={t("optionName")}
                  value={option.name}
                  onChange={(event) =>
                    set({
                      options: draft.options.map((item, i) =>
                        i === index ? { ...item, name: event.target.value } : item,
                      ),
                    })
                  }
                />
                <Input
                  label={t("optionPrice")}
                  inputMode="decimal"
                  value={option.price}
                  onChange={(event) =>
                    set({
                      options: draft.options.map((item, i) =>
                        i === index ? { ...item, price: event.target.value } : item,
                      ),
                    })
                  }
                />
                <Button
                  variant="quiet"
                  onClick={() => set({ options: draft.options.filter((_, i) => i !== index) })}
                >
                  <Trash aria-hidden size={20} />
                  {t("removeOption")}
                </Button>
              </div>
            ))}
            <Button
              variant="secondary"
              onClick={() => set({ options: [...draft.options, { name: "", price: "" }] })}
            >
              <Plus aria-hidden size={20} weight="bold" />
              {t("addOption")}
            </Button>
          </fieldset>

          {error && (
            <p role="alert" className="text-alerte font-bold">
              {error}
            </p>
          )}
          <Button size="lg" fullWidth disabled={busy} onClick={() => void save()}>
            {t("save")}
          </Button>
          {editing !== "new" && editing !== null && (
            <Button variant="quiet" disabled={busy} onClick={() => void remove()}>
              <Trash aria-hidden size={20} />
              {t("remove")}
            </Button>
          )}
        </div>
      </Sheet>
    </SectionFrame>
  );
}
