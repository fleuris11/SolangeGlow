"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { announceArrival } from "@/lib/api/pros";

// The dialog is downloaded when the button is tapped, not with the page (ADR-004).
const BookSheet = dynamic(() => import("./book-sheet").then((m) => m.BookSheet));

type Props = {
  name: string;
  shortLink: string;
  whatsapp?: string;
  directionsUrl?: string | null;
  /** Drawn by the server page: no icon code is sent to the phone. */
  icons: { book: ReactNode; directions: ReactNode; share: ReactNode };
};

/** The main action (book), then directions and sharing. */
export function ShowcaseActions({ name, shortLink, whatsapp, directionsUrl, icons }: Props) {
  const t = useTranslations("pros.showcase");
  const toast = useToast();
  const [bookOpen, setBookOpen] = useState(false);

  const share = async () => {
    const data = { title: name, text: t("shareText", { name }), url: shortLink };
    if (navigator.share) {
      try {
        await navigator.share(data);
      } catch {
        // Closed by the person: nothing to do.
      }
      return;
    }
    await navigator.clipboard?.writeText(shortLink);
    toast(t("linkCopied"), "success");
  };

  return (
    <div className="flex flex-col gap-3">
      <Button size="lg" fullWidth onClick={() => setBookOpen(true)}>
        {icons.book}
        {t("book")}
      </Button>
      <div className="grid grid-cols-2 gap-3">
        {directionsUrl ? (
          <a
            href={directionsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClasses({ variant: "secondary", fullWidth: true })}
          >
            {icons.directions}
            {t("directions")}
          </a>
        ) : null}
        <Button
          variant="secondary"
          fullWidth
          onClick={() => void share()}
          className={directionsUrl ? undefined : "col-span-2"}
        >
          {icons.share}
          {t("share")}
        </Button>
      </div>
      {bookOpen && (
        <BookSheet open={bookOpen} onOpenChange={setBookOpen} name={name} whatsapp={whatsapp} />
      )}
    </div>
  );
}

/** « I am outside »: one tap, the pro gets an alert. */
export function ArrivalButton({
  slug,
  name,
  icon,
}: {
  slug: string;
  name: string;
  icon: ReactNode;
}) {
  const t = useTranslations("pros.showcase");
  const toast = useToast();
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");

  const send = async () => {
    setState("sending");
    try {
      await announceArrival(slug);
      setState("sent");
      toast(t("arrivedSent", { name }), "success");
    } catch (error) {
      setState("idle");
      const message =
        error instanceof ApiError && error.code === "identity_required"
          ? t("arrivedSignIn")
          : error instanceof ApiError
            ? error.message
            : t("arrivedError");
      toast(message, "warning");
    }
  };

  return (
    <div className="bg-poudre rounded-card flex flex-col gap-2 p-4">
      <Button variant="secondary" fullWidth disabled={state !== "idle"} onClick={() => void send()}>
        {icon}
        {state === "sent" ? t("arrivedDone") : t("arrived")}
      </Button>
      <p className="text-small text-prune-doux">{t("arrivedHelp", { name })}</p>
    </div>
  );
}
