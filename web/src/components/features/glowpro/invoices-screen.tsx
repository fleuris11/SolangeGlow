"use client";

import { FilePdf, Receipt } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  creditDocument,
  getBilling,
  getDocuments,
  updateBilling,
  type Document,
} from "@/lib/api/glowpro";
import { formatMoney } from "@/lib/money";

/** « Invoices »: every invoice, receipt and credit note, the PDF, her legal details. */
export function InvoicesScreen() {
  const t = useTranslations("glowpro.invoices");
  const tKind = useTranslations("glowpro.documentKinds");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["documents"], queryFn: getDocuments });
  const [details, setDetails] = useState(false);
  const [cancelling, setCancelling] = useState<Document | null>(null);
  const rows = query.data?.results ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <Receipt aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} />
      </div>
      <p className="text-prune-doux">{t("help")}</p>
      <Button variant="secondary" fullWidth onClick={() => setDetails(true)}>
        {t("details")}
      </Button>
      {query.data && !query.data.einvoice_connected && (
        <p className="text-small text-prune-doux">{t("einvoiceLater")}</p>
      )}
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<Receipt size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((doc) => (
            <li
              key={doc.id}
              className="border-trait bg-carte rounded-card flex min-h-16 items-center gap-3 border p-3"
            >
              <a
                href={doc.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-w-0 flex-1 items-center gap-3"
                aria-label={t("open", { number: doc.number })}
              >
                <FilePdf aria-hidden size={26} className="text-hibiscus shrink-0" />
                <span className="flex min-w-0 flex-col">
                  <span className="font-bold">{doc.number}</span>
                  <span className="text-small text-prune-doux truncate">
                    {tKind(doc.kind)}, {doc.buyer_name}
                    {doc.cancelled && `, ${t("cancelled")}`}
                  </span>
                </span>
              </a>
              <span className="shrink-0 text-right">
                <span className="block font-bold">
                  {formatMoney(doc.total_minor, doc.currency, locale)}
                </span>
                {doc.kind !== "credit_note" && !doc.cancelled && (
                  <button
                    type="button"
                    className="text-small min-h-12 underline"
                    onClick={() => setCancelling(doc)}
                  >
                    {t("cancel")}
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {details && <BillingSheet onClose={() => setDetails(false)} />}
      {cancelling && <CreditSheet document={cancelling} onClose={() => setCancelling(null)} />}
    </div>
  );
}

function BillingSheet({ onClose }: { onClose: () => void }) {
  const t = useTranslations("glowpro.invoices");
  const toast = useToast();
  const query = useQuery({ queryKey: ["billing"], queryFn: getBilling });
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const data = query.data;
  const field = (
    key: "legal_name" | "address" | "registration" | "vat_number" | "vat_mention" | "footer",
  ) => values[key] ?? data?.[key] ?? "";

  const save = async () => {
    setBusy(true);
    try {
      await updateBilling(values);
      toast(t("saved"), "success");
      onClose();
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
      title={t("details")}
      description={t("detailsHelp")}
    >
      {!data ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : (
        <div className="flex flex-col gap-4">
          {(
            [
              "legal_name",
              "address",
              "registration",
              "vat_number",
              "vat_mention",
              "footer",
            ] as const
          ).map((key) => (
            <Input
              key={key}
              label={t(`fields.${key}`)}
              value={field(key)}
              onChange={(e) => setValues({ ...values, [key]: e.target.value })}
            />
          ))}
          <Button size="lg" fullWidth disabled={busy} onClick={() => void save()}>
            {t("save")}
          </Button>
        </div>
      )}
    </Sheet>
  );
}

function CreditSheet({ document, onClose }: { document: Document; onClose: () => void }) {
  const t = useTranslations("glowpro.invoices");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      await creditDocument(document.id, reason);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast(t("credited"), "success");
      onClose();
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
      title={t("cancelTitle", { number: document.number })}
      description={t("cancelHelp")}
    >
      <div className="flex flex-col gap-4">
        <Input
          label={t("reason")}
          value={reason}
          maxLength={200}
          onChange={(e) => setReason(e.target.value)}
        />
        <Button size="lg" fullWidth disabled={busy || !reason.trim()} onClick={() => void save()}>
          {t("cancelConfirm")}
        </Button>
      </div>
    </Sheet>
  );
}
