"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import type { StoryGroup } from "@/lib/api/social";
import { mediaSrc } from "@/lib/media";

const StorySheet = dynamic(() => import("./story-sheet").then((m) => m.StorySheet));

/** Today's stories: one avatar per person, with the Glow ring until her stories are seen. */
export function StoryStrip({ groups }: { groups: StoryGroup[] }) {
  const t = useTranslations("social.stories");
  const [openAt, setOpenAt] = useState<number | null>(null);
  const [seenAuthors, setSeenAuthors] = useState<string[]>(() =>
    groups.filter((group) => group.seen).map((group) => group.author.id),
  );
  if (groups.length === 0) return null;

  return (
    <section aria-labelledby="stories-title" className="flex flex-col gap-3">
      <h2 id="stories-title" className="text-title font-bold">
        {t("title")}
      </h2>
      <ul className="relative -mx-4 flex [scrollbar-width:none] gap-3 overflow-x-auto px-4 pb-1">
        {groups.map((group, index) => {
          const seen = seenAuthors.includes(group.author.id);
          const hasSlots = group.stories.some((story) => story.kind === "free_slots");
          return (
            <li key={group.author.id} className="shrink-0">
              <button
                type="button"
                onClick={() => setOpenAt(index)}
                className="flex w-20 flex-col items-center gap-1 text-center"
              >
                <Avatar
                  name={group.author.name}
                  src={mediaSrc(group.author.photo, "thumb", "medium")}
                  size="md"
                  halo={!seen}
                />
                <span className="text-mention w-full truncate font-bold">{group.author.name}</span>
                {hasSlots && (
                  <span className="bg-feuille text-lait text-mention rounded-full px-2 font-bold">
                    {t("freeSlots")}
                  </span>
                )}
                <span className="sr-only">{seen ? t("seen") : t("new")}</span>
              </button>
            </li>
          );
        })}
      </ul>
      {openAt !== null && (
        <StorySheet
          groups={groups}
          startAt={openAt}
          onShown={(authorId) =>
            setSeenAuthors((current) =>
              current.includes(authorId) ? current : [...current, authorId],
            )
          }
          onClose={() => setOpenAt(null)}
        />
      )}
    </section>
  );
}
