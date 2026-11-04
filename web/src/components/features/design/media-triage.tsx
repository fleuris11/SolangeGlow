"use client";

import { useLocale, useTranslations } from "next-intl";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { useToast } from "@/components/ui/toast";

type Item = {
  slug: string;
  kind: string;
  category: string;
  src: string;
  poster?: string;
  author: string;
  source: string;
  license: string;
  page: string;
};
type Choice = "keep" | "reject";

const STORAGE_KEY = "sg.media-triage";

/** The owner sorts the demonstration media: kept on this device, then copied as a list. */
export function MediaTriage({ items }: { items: Item[] }) {
  const t = useTranslations("design.media");
  const locale = useLocale();
  const toast = useToast();
  const [choices, setChoices] = useState<Record<string, Choice>>({});

  useEffect(() => {
    try {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- read once from the device
      setChoices(JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}"));
    } catch {
      // Blocked storage: the sorting still works for this visit.
    }
  }, []);

  function choose(slug: string, choice: Choice) {
    const next = { ...choices, [slug]: choice };
    setChoices(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Blocked storage: same.
    }
  }

  const rejected = useMemo(
    () => Object.keys(choices).filter((slug) => choices[slug] === "reject"),
    [choices],
  );
  const kept = items.length - rejected.length;
  const count = new Intl.NumberFormat(locale);

  async function copy() {
    await navigator.clipboard?.writeText(rejected.join("\n"));
    toast(t("copied"));
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-bold">
          {t("summary", { kept: count.format(kept), rejected: count.format(rejected.length) })}
        </p>
        <Button variant="secondary" onClick={copy} disabled={rejected.length === 0}>
          {t("copy")}
        </Button>
      </div>
      <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {items.map((item) => (
          <li key={item.slug} className="flex min-w-0 flex-col gap-2">
            <div className="rounded-photo bg-poudre relative aspect-[4/5] overflow-hidden">
              <Image
                src={item.kind === "video" ? (item.poster ?? item.src) : item.src}
                alt=""
                fill
                sizes="(min-width: 1024px) 25vw, 50vw"
                className={
                  choices[item.slug] === "reject" ? "object-cover opacity-30" : "object-cover"
                }
              />
            </div>
            <p className="text-small font-bold">{item.slug}</p>
            <p className="text-mention text-prune-doux">
              {item.category}, {item.author || t("noAuthor")}, {item.source}
            </p>
            <div className="flex gap-2">
              <Chip
                selected={choices[item.slug] !== "reject"}
                onClick={() => choose(item.slug, "keep")}
              >
                {t("keep")}
              </Chip>
              <Chip
                selected={choices[item.slug] === "reject"}
                onClick={() => choose(item.slug, "reject")}
              >
                {t("reject")}
              </Chip>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
