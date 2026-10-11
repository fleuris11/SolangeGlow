"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { searchPros, type ProCard as Card, type SearchQuery } from "@/lib/api/pros";

// The first page of cards comes from the server; this code is only for the next ones.
const ProCard = dynamic(() => import("../pro-card").then((m) => m.ProCard));

/** « See more pros »: the next pages of the search, added under the first one. */
export function LoadMore({ query, next }: { query: SearchQuery; next: string | null }) {
  const t = useTranslations("explore");
  const [cards, setCards] = useState<Card[]>([]);
  const [cursor, setCursor] = useState(next);
  const [busy, setBusy] = useState(false);

  const more = async () => {
    if (!cursor) return;
    setBusy(true);
    try {
      const page = await searchPros({ ...query, cursor });
      setCards((current) => [...current, ...page.results]);
      setCursor(page.next ?? null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {cards.length > 0 && (
        <ul className="flex flex-col gap-3">
          {cards.map((pro) => (
            <li key={pro.slug}>
              <ProCard pro={pro} />
            </li>
          ))}
        </ul>
      )}
      {cursor && (
        <Button variant="secondary" disabled={busy} onClick={() => void more()}>
          {t("more")}
        </Button>
      )}
    </>
  );
}
