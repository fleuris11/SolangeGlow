"use client";

import { CalendarCheck, CaretLeft, CaretRight, ChatCircleText } from "@phosphor-icons/react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { hasSession } from "@/lib/api/client";
import { markStorySeen } from "@/lib/api/feed";
import type { StoryGroup } from "@/lib/api/social";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc, videoSrc } from "@/lib/media";
import { formatClock } from "@/lib/pros/format";

import { WriteButton } from "@/components/features/messaging/write-button";

/** "14:00" today, on this phone's clock. */
function todayAt(slot: string): Date {
  const [hours = 0, minutes = 0] = slot.split(":").map(Number);
  const date = new Date();
  date.setHours(hours, minutes, 0, 0);
  return date;
}

const COLOURS: Record<string, string> = {
  hibiscus: "bg-hibiscus text-sur-hibiscus",
  prune: "bg-prune text-lait",
  or: "bg-or text-sur-or",
  feuille: "bg-feuille text-lait",
  poudre: "bg-poudre text-prune",
};

type Props = {
  groups: StoryGroup[];
  startAt: number;
  onShown: (authorId: string) => void;
  onClose: () => void;
};

/** Stories in a bottom sheet, one at a time: the person moves on with the buttons. */
export function StorySheet({ groups, startAt, onShown, onClose }: Props) {
  const t = useTranslations("social.stories");
  const locale = useLocale();
  const items = groups.flatMap((group) => group.stories.map((story) => ({ group, story })));
  const first = items.findIndex((item) => item.group === groups[startAt]);
  const [position, setPosition] = useState(Math.max(first, 0));
  const current = items[position];
  const shown = useRef(onShown);
  useEffect(() => {
    shown.current = onShown;
  });
  const storyId = current?.story.id;

  // Each story shown once is marked as seen (and the person, after her last story).
  useEffect(() => {
    const item = items.find((entry) => entry.story.id === storyId);
    if (!item) return;
    if (hasSession()) void markStorySeen(item.story.id).catch(() => undefined);
    const last = item.group.stories[item.group.stories.length - 1];
    if (last?.id === item.story.id) shown.current(item.group.author.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyId]);

  if (!current) return null;
  const { group, story } = current;
  const inGroup = group.stories.indexOf(story) + 1;
  const picture = mediaSrc(story.media, "large", "medium");
  const video = story.kind === "video" ? videoSrc(story.media, false) : undefined;

  return (
    <Sheet
      open
      onOpenChange={(open) => !open && onClose()}
      title={group.author.name}
      description={t("position", { index: inGroup, count: group.stories.length })}
    >
      <div className="flex flex-col gap-4">
        {story.kind === "free_slots" ? (
          <div className="bg-poudre rounded-card flex flex-col gap-3 p-5">
            <p className="text-lead font-bold">{t("slotsTitle")}</p>
            <ul className="flex flex-wrap gap-2">
              {story.slots.map((slot) => (
                <li
                  key={slot}
                  className="bg-carte font-display text-title rounded-full px-4 py-2 font-black"
                >
                  {formatClock(slot, locale)}
                </li>
              ))}
            </ul>
            {group.author.pro_slug && !story.is_mine && (
              <div className="flex flex-col gap-2">
                <p className="text-small font-bold">{t("askSlot")}</p>
                <div className="flex flex-wrap gap-2">
                  {story.slots.map((slot) => (
                    <WriteButton
                      key={slot}
                      personId={group.author.id}
                      icon={<ChatCircleText aria-hidden size={20} weight="bold" />}
                      label={t("writeFor", { time: formatClock(slot, locale) })}
                      query={`slot=${encodeURIComponent(
                        `${group.author.pro_slug}|${todayAt(slot).toISOString()}`,
                      )}`}
                    />
                  ))}
                </div>
              </div>
            )}
            {group.author.pro_slug && (
              <Link
                href={`/${group.author.pro_slug}`}
                className={buttonClasses({ fullWidth: true })}
              >
                <CalendarCheck aria-hidden size={22} weight="bold" />
                {t("book")}
              </Link>
            )}
          </div>
        ) : story.kind === "text" ? (
          <p
            className={cn(
              "rounded-card font-display text-headline flex min-h-64 items-center justify-center p-6 text-center font-black",
              COLOURS[story.background] ?? COLOURS.hibiscus,
            )}
          >
            {story.text}
          </p>
        ) : video ? (
          <video src={video} controls playsInline className="rounded-card w-full" />
        ) : picture ? (
          // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
          <img
            src={picture}
            alt={story.text || group.author.name}
            className="rounded-card w-full"
          />
        ) : null}
        {story.text && story.kind !== "text" && <p>{story.text}</p>}

        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="secondary"
            disabled={position === 0}
            onClick={() => setPosition(position - 1)}
          >
            <CaretLeft aria-hidden size={22} weight="bold" />
            {t("previous")}
          </Button>
          <Button
            onClick={() => (position + 1 < items.length ? setPosition(position + 1) : onClose())}
          >
            {position + 1 < items.length ? t("next") : t("done")}
            <CaretRight aria-hidden size={22} weight="bold" />
          </Button>
        </div>
      </div>
    </Sheet>
  );
}
